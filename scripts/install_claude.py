from __future__ import annotations

import json
from pathlib import Path

from policy.claude import (
    CLAUDE_DOCTRINE_END,
    CLAUDE_DOCTRINE_START,
    SHELL_LAUNCHER_END,
    SHELL_LAUNCHER_START,
    claude_profiles,
    format_doctrine,
    managed_hook_commands,
    render_hooks,
    shell_launcher_body,
    skill_sources,
    skill_targets,
)
from policy.shared import HOME, dump_json, load_json, read_text, replace_or_append_block, write_text
from scripts.audit_bash_aliases import audit_file
from scripts.install_common import diff_text, manage_skill_link, manage_state_dir, result


def _ensure_doctrine(path: Path, label: str, apply: bool, dry_run: bool) -> object:
    old = read_text(path)
    new = replace_or_append_block(old, CLAUDE_DOCTRINE_START, CLAUDE_DOCTRINE_END, "\n".join(format_doctrine().splitlines()[1:-1]))
    if old == new:
        return result(label, "already_ok", "Doctrine block in sync", path)
    if not apply:
        return result(label, "missing", "Doctrine block missing or drifted", path, diff_text(old, new, str(path)))
    write_text(path, new, dry_run=dry_run)
    return result(label, "configured", "Doctrine block updated", path, diff_text(old, new, str(path)))


def strip_managed_hooks(data: dict, repo_root: Path) -> dict:
    commands = managed_hook_commands(repo_root)
    hooks = dict(data.get("hooks", {}))
    for event, entries in list(hooks.items()):
        kept = []
        for entry in entries:
            entry_hooks = entry.get("hooks", [])
            filtered = [hook for hook in entry_hooks if hook.get("command") not in commands]
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
    data["hooks"] = hooks
    return data


def merge_hooks(settings_path: Path, repo_root: Path, apply: bool, dry_run: bool) -> object:
    label = f"{settings_path.parent.name}/settings.json hooks"
    old_data = load_json(settings_path, {})
    new_data = json.loads(json.dumps(old_data))
    new_data = strip_managed_hooks(new_data, repo_root)
    hooks = new_data.setdefault("hooks", {})
    for event, entries in render_hooks(repo_root).items():
        hooks.setdefault(event, [])
        hooks[event].extend(entries)
    old_text = dump_json(old_data)
    new_text = dump_json(new_data)
    if old_text == new_text:
        return result(label, "already_ok", "Claude hooks in sync", settings_path)
    if not apply:
        return result(label, "missing", "Claude hooks missing or drifted", settings_path, diff_text(old_text, new_text, str(settings_path)))
    write_text(settings_path, new_text, dry_run=dry_run)
    return result(label, "configured", "Claude hooks merged", settings_path, diff_text(old_text, new_text, str(settings_path)))


def strip_legacy_shell_launchers(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    skip_aliases = {"alias claude1=", "alias claude2=", "alias claude="}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("function claude()") or stripped.startswith("claude() {"):
            depth = 0
            while i < len(lines):
                current = lines[i]
                depth += current.count("{")
                depth -= current.count("}")
                i += 1
                if depth <= 0 and current.strip() == "}":
                    break
            continue
        if any(stripped.startswith(prefix) for prefix in skip_aliases):
            i += 1
            continue
        kept.append(line)
        i += 1
    return "\n".join(kept).rstrip() + "\n"


def manage_shell(path: Path, apply: bool, dry_run: bool, adopt_legacy: bool) -> object:
    label = "shell/.bash_aliases"
    old = read_text(path)
    audit = audit_file(path)
    shadowing = [item for item in audit["shadowing"] if item["name"] in {"claude", "claude1", "claude2"}]
    if shadowing and not adopt_legacy:
        return result(label, "warning", "Unmanaged Claude launchers exist outside the managed block", path)
    base = strip_legacy_shell_launchers(old) if adopt_legacy else old
    new = replace_or_append_block(base, SHELL_LAUNCHER_START, SHELL_LAUNCHER_END, shell_launcher_body())
    if old == new:
        return result(label, "already_ok", "Shell launcher block in sync", path)
    if not apply:
        return result(label, "missing", "Shell launcher block missing or drifted", path, diff_text(old, new, str(path)))
    write_text(path, new, dry_run=dry_run)
    return result(label, "configured", "Shell launcher block updated", path, diff_text(old, new, str(path)))


def install_claude(*, apply: bool, dry_run: bool, include_shell: bool, profiles: set[str], adopt_legacy_shell_profiles: bool, home: Path = HOME, repo_root: Path | None = None) -> list:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: list = []
    profile_map = claude_profiles(home)
    selected_profiles = {name: profile_map[name] for name in profiles}
    for profile in selected_profiles.values():
        results.append(_ensure_doctrine(profile.config_root / "CLAUDE.md", f"claude({profile.name})/CLAUDE.md", apply, dry_run))
        results.append(merge_hooks(profile.config_root / "settings.json", repo_root, apply, dry_run))
    results.append(manage_state_dir(apply, dry_run))
    sources = skill_sources(repo_root)
    for profile in selected_profiles.values():
        for name, target in skill_targets(profile).items():
            results.append(manage_skill_link(target, sources[name], f"claude({profile.name})/skills/{name}", apply, dry_run))
    if include_shell:
        results.append(manage_shell(home / ".bash_aliases", apply, dry_run, adopt_legacy_shell_profiles))
    return results
