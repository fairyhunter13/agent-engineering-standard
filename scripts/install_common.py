from __future__ import annotations

import difflib
from pathlib import Path

from policy.shared import Result, STATE_DIR, ensure_directory, replace_symlink, symlink_points_to


def diff_text(old: str, new: str, label: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{label} (old)",
            tofile=f"{label} (new)",
            n=2,
        )
    )


def result(tool: str, status: str, message: str, path: Path | None = None, diff: str = "") -> Result:
    return Result(tool=tool, status=status, message=message, path=str(path) if path else "", diff=diff)


def manage_skill_link(target: Path, source: Path, label: str, apply: bool, dry_run: bool) -> Result:
    if symlink_points_to(target, source):
        return result(label, "already_ok", "Skill symlink in sync", target)
    message = "Skill target exists as a real path" if target.exists() and not target.is_symlink() else "Skill symlink missing or wrong target"
    if not apply:
        return result(label, "missing", message, target, f"{target} -> {source}")
    replace_symlink(target, source, dry_run=dry_run)
    return result(label, "configured", "Skill symlink updated", target, f"{target} -> {source}")


def manage_state_dir(apply: bool, dry_run: bool) -> Result:
    if STATE_DIR.exists():
        return result("state-dir", "already_ok", "State directory exists", STATE_DIR)
    if not apply:
        return result("state-dir", "missing", "State directory missing", STATE_DIR)
    ensure_directory(STATE_DIR, dry_run=dry_run)
    return result("state-dir", "configured", "State directory created", STATE_DIR)
