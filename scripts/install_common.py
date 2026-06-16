from __future__ import annotations

import difflib
from pathlib import Path

from policy.shared import Result, STATE_DIR, dump_json, ensure_directory, load_json, read_text, replace_or_append_block, replace_symlink, symlink_points_to, write_text


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


def ensure_managed_block(path: Path, *, start: str, end: str, body: str, label: str, apply: bool, dry_run: bool) -> Result:
    old = read_text(path)
    new = replace_or_append_block(old, start, end, body)
    if old == new:
        return result(label, "already_ok", "Doctrine block in sync", path)
    if not apply:
        return result(label, "missing", "Doctrine block missing or drifted", path, diff_text(old, new, str(path)))
    write_text(path, new, dry_run=dry_run)
    return result(label, "configured", "Doctrine block updated", path, diff_text(old, new, str(path)))


def merge_hook_entries(
    settings_path: Path,
    *,
    rendered_hooks: dict,
    strip_commands: set[str],
    apply: bool,
    dry_run: bool,
    label: str,
    missing_message: str,
    configured_message: str,
    synced_message: str,
) -> Result:
    old_data = load_json(settings_path, {})
    new_data = load_json(settings_path, {})
    hooks = dict(new_data.get("hooks", {}))
    for event, entries in list(hooks.items()):
        kept = []
        for entry in entries:
            entry_hooks = entry.get("hooks", [])
            filtered = [hook for hook in entry_hooks if hook.get("command") not in strip_commands]
            if filtered:
                kept.append({**entry, "hooks": filtered})
            elif entry_hooks and filtered != entry_hooks:
                continue
            else:
                kept.append(entry)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    new_data["hooks"] = hooks
    merged = new_data.setdefault("hooks", {})
    for event, entries in rendered_hooks.items():
        merged.setdefault(event, [])
        merged[event].extend(entries)
    old_text = dump_json(old_data)
    new_text = dump_json(new_data)
    if old_text == new_text:
        return result(label, "already_ok", synced_message, settings_path)
    if not apply:
        return result(label, "missing", missing_message, settings_path, diff_text(old_text, new_text, str(settings_path)))
    write_text(settings_path, new_text, dry_run=dry_run)
    return result(label, "configured", configured_message, settings_path, diff_text(old_text, new_text, str(settings_path)))


def manage_owned_json(path: Path, *, rendered: dict, apply: bool, dry_run: bool, label: str, missing_message: str, configured_message: str, synced_message: str) -> Result:
    old_text = read_text(path)
    new_text = dump_json(rendered)
    if old_text.strip() == new_text.strip():
        return result(label, "already_ok", synced_message, path)
    if not apply:
        return result(label, "missing", missing_message, path, diff_text(old_text, new_text, str(path)))
    write_text(path, new_text, dry_run=dry_run)
    return result(label, "configured", configured_message, path, diff_text(old_text, new_text, str(path)))
