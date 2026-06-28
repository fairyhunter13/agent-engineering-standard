from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from hooks.worktree_clean import clean_worktrees


# ── helpers ──────────────────────────────────────────────────────────────────

def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _make_repo(path: Path) -> None:
    """Init a git repo with one commit."""
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "user.name", "Test")
    (path / "README.md").write_text("init\n")
    _git(path, "add", ".")
    _git(path, "commit", "-m", "init")


def _add_agent_worktree(repo: Path, name: str) -> Path:
    """Create a worktree-agent-<name> branch + checkout under .claude/worktrees/."""
    wt_path = repo / ".claude" / "worktrees" / f"agent-{name}"
    wt_path.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-b", f"worktree-agent-{name}", str(wt_path))
    return wt_path


def _make_old(path: Path, age_s: int = 3600) -> None:
    """Back-date mtime so it appears older than the default threshold."""
    t = time.time() - age_s
    os.utime(path, (t, t))


# ── tests ─────────────────────────────────────────────────────────────────────

def test_noop_outside_git_repo(tmp_path: Path) -> None:
    removed = clean_worktrees(tmp_path)
    assert removed == []


def test_removes_merged_old_clean_worktree(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    wt = _add_agent_worktree(tmp_path, "abc1")
    _make_old(wt)
    removed = clean_worktrees(tmp_path, max_age_s=1)
    assert str(wt) in removed
    assert not wt.exists()
    branches = subprocess.run(
        ["git", "-C", str(tmp_path), "branch"], capture_output=True, text=True
    ).stdout
    assert "worktree-agent-abc1" not in branches


def test_keeps_worktree_with_unmerged_commits(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    wt = _add_agent_worktree(tmp_path, "abc2")
    # commit something in the worktree so its HEAD diverges from main
    (wt / "extra.txt").write_text("work\n")
    _git(wt, "add", ".")
    _git(wt, "commit", "-m", "agent work")
    _make_old(wt)
    removed = clean_worktrees(tmp_path, max_age_s=1)
    assert str(wt) not in removed
    assert wt.exists()


def test_keeps_recent_worktree(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    wt = _add_agent_worktree(tmp_path, "abc3")
    # do NOT back-date → mtime is now, threshold is 30 min by default
    removed = clean_worktrees(tmp_path, max_age_s=3600)
    assert str(wt) not in removed
    assert wt.exists()


def test_keeps_locked_worktree(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    wt = _add_agent_worktree(tmp_path, "abc4")
    _git(tmp_path, "worktree", "lock", str(wt))
    _make_old(wt)
    removed = clean_worktrees(tmp_path, max_age_s=1)
    assert str(wt) not in removed
    assert wt.exists()


def test_keeps_worktree_with_tracked_dirty_changes(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    wt = _add_agent_worktree(tmp_path, "abc5")
    # Stage a tracked change (not just untracked)
    (wt / "README.md").write_text("modified\n")
    _make_old(wt)
    removed = clean_worktrees(tmp_path, max_age_s=1)
    assert str(wt) not in removed
    assert wt.exists()


def test_ignores_untracked_leakage(tmp_path: Path) -> None:
    """Untracked files (e.g. skills/catalog/ leakage) must not block removal."""
    _make_repo(tmp_path)
    wt = _add_agent_worktree(tmp_path, "abc6")
    # Drop an untracked file — simulates the skills/catalog/ leakage we observed
    (wt / "untracked.txt").write_text("junk\n")
    _make_old(wt)
    removed = clean_worktrees(tmp_path, max_age_s=1)
    assert str(wt) in removed
