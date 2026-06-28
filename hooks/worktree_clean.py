#!/usr/bin/env python3
"""Auto-clean orphaned `worktree-agent-*` git worktrees.

A worktree is removed only when ALL guards pass:
  1. Branch starts with ``worktree-agent-`` (agent-isolation pattern).
  2. Not locked (per ``git worktree list --porcelain``).
  3. Directory mtime older than threshold (default 30 min; AES_WORKTREE_MAX_AGE_MIN env).
  4. No uncommitted *tracked* changes (untracked ``??`` leakage is ignored).
  5. HEAD is an ancestor of the primary worktree HEAD (no unmerged commits).
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

_DEFAULT_MAX_AGE_S = 30 * 60


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def _git_root(cwd: Path) -> Path | None:
    r = _run(["git", "rev-parse", "--show-toplevel"], cwd)
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def _primary_head(root: Path) -> str | None:
    r = _run(["git", "rev-parse", "HEAD"], root)
    return r.stdout.strip() if r.returncode == 0 else None


def _parse_worktrees(root: Path) -> list[dict]:
    """Parse ``git worktree list --porcelain`` into a list of dicts."""
    r = _run(["git", "worktree", "list", "--porcelain"], root)
    if r.returncode != 0:
        return []
    entries: list[dict] = []
    current: dict = {}
    for line in r.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            current = {"path": line[9:].strip()}
        elif line.startswith("HEAD "):
            current["head"] = line[5:].strip()
        elif line.startswith("branch "):
            b = line[7:].strip()
            if b.startswith("refs/heads/"):
                b = b[11:]
            current["branch"] = b
        elif line == "locked" or line.startswith("locked "):
            current["locked"] = True
    if current:
        entries.append(current)
    return entries


def _agent_worktrees(root: Path) -> list[dict]:
    """Return linked worktrees whose branch matches ``worktree-agent-*``."""
    all_wts = _parse_worktrees(root)
    # first entry is the primary worktree; skip it
    return [
        wt for wt in all_wts[1:]
        if wt.get("branch", "").startswith("worktree-agent-")
    ]


def _is_safe(wt: dict, primary_head: str, root: Path, max_age_s: int) -> bool:
    """Return True only when all guards pass."""
    if wt.get("locked"):
        return False
    wt_path = Path(wt["path"])
    if not wt_path.exists():
        return True  # prunable; no changes possible
    if time.time() - wt_path.stat().st_mtime < max_age_s:
        return False
    # tracked-changes guard (ignore untracked lines starting with ??)
    status = _run(["git", "status", "--porcelain=v1"], wt_path)
    if status.returncode != 0:
        return False
    if any(
        not line.startswith("??") and not line.startswith("!!")
        for line in status.stdout.splitlines()
        if line.strip()
    ):
        return False
    # merged-commits guard
    wt_head = wt.get("head")
    if not wt_head:
        return False
    r = _run(["git", "merge-base", "--is-ancestor", wt_head, primary_head], root)
    return r.returncode == 0


def clean_worktrees(cwd: Path | None = None, max_age_s: int | None = None) -> list[str]:
    """Remove safe orphaned agent worktrees. Returns list of removed paths."""
    if max_age_s is None:
        try:
            max_age_s = int(os.environ.get("AES_WORKTREE_MAX_AGE_MIN", "30")) * 60
        except (ValueError, TypeError):
            max_age_s = _DEFAULT_MAX_AGE_S
    root = _git_root(cwd or Path.cwd())
    if root is None:
        return []
    primary_head = _primary_head(root)
    if not primary_head:
        return []
    removed: list[str] = []
    for wt in _agent_worktrees(root):
        if not _is_safe(wt, primary_head, root, max_age_s):
            continue
        r = _run(["git", "worktree", "remove", "--force", wt["path"]], root)
        if r.returncode == 0:
            removed.append(wt["path"])
            branch = wt.get("branch")
            if branch:
                _run(["git", "branch", "-D", branch], root)
    _run(["git", "worktree", "prune"], root)
    return removed
