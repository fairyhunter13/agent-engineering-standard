#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.canonical import (  # noqa: E402
    CLAUDE_DOCTRINE_END,
    CLAUDE_DOCTRINE_START,
    CODEX_DOCTRINE_END,
    CODEX_DOCTRINE_START,
    HOME,
    Result,
    SHELL_LAUNCHER_END,
    SHELL_LAUNCHER_START,
    STATE_DIR,
    claude_profiles,
    claude_skill_sources,
    claude_skill_targets,
    codex_skill_targets,
    dump_json,
    ensure_directory,
    format_claude_doctrine,
    format_codex_doctrine,
    load_json,
    managed_hook_commands,
    read_text,
    render_claude_hooks,
    render_codex_hooks,
    replace_or_append_block,
    replace_symlink,
    shell_launcher_body,
    symlink_points_to,
    write_text,
)
from scripts.audit_bash_aliases import audit_file  # noqa: E402

ALL_TARGETS = {"claude", "codex", "shell", "skills", "hooks"}
DEFAULT_TARGETS = {"claude", "codex", "skills", "hooks"}


def _diff(old: str, new: str, label: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{label} (old)",
            tofile=f"{label} (new)",
            n=2,
        )
    )


def _result(tool: str, status: str, message: str, path: Path | None = None, diff: str = "") -> Result:
    return Result(tool=tool, status=status, message=message, path=str(path) if path else "", diff=diff)


def _ensure_doctrine(path: Path, start: str, end: str, body: str, label: str, apply: bool, dry_run: bool) -> Result:
    old = read_text(path)
    new = replace_or_append_block(old, start, end, body)
    if old == new:
        return _result(label, "already_ok", "Doctrine block in sync", path)
    if not apply:
        return _result(label, "missing", "Doctrine block missing or drifted", path, _diff(old, new, str(path)))
    write_text(path, new, dry_run=dry_run)
    return _result(label, "configured", "Doctrine block updated", path, _diff(old, new, str(path)))


def _strip_managed_claude_hooks(data: dict, repo_root: Path) -> dict:
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


def _merge_claude_hooks(settings_path: Path, repo_root: Path, apply: bool, dry_run: bool) -> Result:
    label = f"{settings_path.parent.name}/settings.json hooks"
    old_data = load_json(settings_path, {})
    new_data = json.loads(json.dumps(old_data))
    new_data = _strip_managed_claude_hooks(new_data, repo_root)
    hooks = new_data.setdefault("hooks", {})
    for event, entries in render_claude_hooks(repo_root).items():
        hooks.setdefault(event, [])
        hooks[event].extend(entries)
    old_text = dump_json(old_data)
    new_text = dump_json(new_data)
    if old_text == new_text:
        return _result(label, "already_ok", "Claude hooks in sync", settings_path)
    if not apply:
        return _result(label, "missing", "Claude hooks missing or drifted", settings_path, _diff(old_text, new_text, str(settings_path)))
    write_text(settings_path, new_text, dry_run=dry_run)
    return _result(label, "configured", "Claude hooks merged", settings_path, _diff(old_text, new_text, str(settings_path)))


def _manage_codex_hooks(path: Path, repo_root: Path, apply: bool, dry_run: bool) -> Result:
    label = "codex/hooks.json"
    old_text = read_text(path)
    new_text = dump_json(render_codex_hooks(repo_root))
    if old_text.strip() == new_text.strip():
        return _result(label, "already_ok", "Codex hooks in sync", path)
    if not apply:
        return _result(label, "missing", "Codex hooks missing or drifted", path, _diff(old_text, new_text, str(path)))
    write_text(path, new_text, dry_run=dry_run)
    return _result(label, "configured", "Codex hooks installed", path, _diff(old_text, new_text, str(path)))


def _manage_skill_link(target: Path, source: Path, label: str, apply: bool, dry_run: bool) -> Result:
    if symlink_points_to(target, source):
        return _result(label, "already_ok", "Skill symlink in sync", target)
    if target.exists() and not target.is_symlink():
        status = "missing"
        message = "Skill target exists as a real path"
    else:
        status = "missing"
        message = "Skill symlink missing or wrong target"
    if not apply:
        return _result(label, status, message, target, f"{target} -> {source}")
    replace_symlink(target, source, dry_run=dry_run)
    return _result(label, "configured", "Skill symlink updated", target, f"{target} -> {source}")


def _strip_legacy_shell_launchers(text: str) -> str:
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


def _manage_shell(path: Path, apply: bool, dry_run: bool, adopt_legacy: bool) -> Result:
    label = "shell/.bash_aliases"
    old = read_text(path)
    audit = audit_file(path)
    shadowing = [item for item in audit["shadowing"] if item["name"] in {"claude", "claude1", "claude2"}]
    if shadowing and not adopt_legacy:
        return _result(label, "warning", "Unmanaged Claude launchers exist outside the managed block", path)
    base = _strip_legacy_shell_launchers(old) if adopt_legacy else old
    new = replace_or_append_block(base, SHELL_LAUNCHER_START, SHELL_LAUNCHER_END, shell_launcher_body())
    if old == new:
        return _result(label, "already_ok", "Shell launcher block in sync", path)
    if not apply:
        return _result(label, "missing", "Shell launcher block missing or drifted", path, _diff(old, new, str(path)))
    write_text(path, new, dry_run=dry_run)
    return _result(label, "configured", "Shell launcher block updated", path, _diff(old, new, str(path)))


def _manage_state_dir(apply: bool, dry_run: bool) -> Result:
    if STATE_DIR.exists():
        return _result("state-dir", "already_ok", "State directory exists", STATE_DIR)
    if not apply:
        return _result("state-dir", "missing", "State directory missing", STATE_DIR)
    ensure_directory(STATE_DIR, dry_run=dry_run)
    return _result("state-dir", "configured", "State directory created", STATE_DIR)


def run_install(
    *,
    apply: bool,
    dry_run: bool,
    targets: set[str],
    profiles: set[str],
    adopt_legacy_shell_profiles: bool,
    home: Path = HOME,
    repo_root: Path | None = None,
) -> list[Result]:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: list[Result] = []
    profile_map = claude_profiles(home)
    selected_profiles = {name: profile_map[name] for name in profiles}

    if "claude" in targets:
        for profile in selected_profiles.values():
            results.append(
                _ensure_doctrine(
                    profile.config_root / "CLAUDE.md",
                    CLAUDE_DOCTRINE_START,
                    CLAUDE_DOCTRINE_END,
                    "\n".join(format_claude_doctrine().splitlines()[1:-1]),
                    f"claude({profile.name})/CLAUDE.md",
                    apply,
                    dry_run,
                )
            )
    if "hooks" in targets:
        for profile in selected_profiles.values():
            results.append(_merge_claude_hooks(profile.config_root / "settings.json", repo_root, apply, dry_run))
        results.append(_manage_state_dir(apply, dry_run))
    if "skills" in targets:
        for profile in selected_profiles.values():
            sources = claude_skill_sources("claude", repo_root)
            for name, target in claude_skill_targets(profile).items():
                results.append(_manage_skill_link(target, sources[name], f"claude({profile.name})/skills/{name}", apply, dry_run))
        codex_sources = claude_skill_sources("codex", repo_root)
        for name, target in codex_skill_targets(home).items():
            results.append(_manage_skill_link(target, codex_sources[name], f"codex-skills/{name}", apply, dry_run))
    if "codex" in targets:
        results.append(
            _ensure_doctrine(
                home / ".codex" / "AGENTS.md",
                CODEX_DOCTRINE_START,
                CODEX_DOCTRINE_END,
                "\n".join(format_codex_doctrine().splitlines()[1:-1]),
                "codex/AGENTS.md",
                apply,
                dry_run,
            )
        )
    if "hooks" in targets or "codex" in targets:
        results.append(_manage_codex_hooks(home / ".codex" / "hooks.json", repo_root, apply, dry_run))
    if "shell" in targets:
        results.append(_manage_shell(home / ".bash_aliases", apply, dry_run, adopt_legacy_shell_profiles))
    return results


def parse_targets(value: str) -> set[str]:
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    invalid = parsed - ALL_TARGETS
    if invalid:
        raise argparse.ArgumentTypeError(f"Unknown targets: {sorted(invalid)}")
    return parsed or set(DEFAULT_TARGETS)


def parse_profiles(value: str) -> set[str]:
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    valid = {"main", "account1", "account2"}
    invalid = parsed - valid
    if invalid:
        raise argparse.ArgumentTypeError(f"Unknown profiles: {sorted(invalid)}")
    return parsed or valid


def main() -> int:
    parser = argparse.ArgumentParser(description="Install global agent engineering policy surfaces.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--targets", type=parse_targets, default=set(DEFAULT_TARGETS))
    parser.add_argument("--profiles", type=parse_profiles, default={"main", "account1", "account2"})
    parser.add_argument("--adopt-legacy-shell-profiles", action="store_true")
    args = parser.parse_args()
    apply = args.apply
    results = run_install(
        apply=apply,
        dry_run=args.dry_run,
        targets=args.targets,
        profiles=args.profiles,
        adopt_legacy_shell_profiles=args.adopt_legacy_shell_profiles,
    )
    if args.json_out:
        print(json.dumps([result.__dict__ for result in results], indent=2))
    else:
        for result in results:
            print(f"[{result.status}] {result.tool}: {result.message}")
    failures = [result for result in results if result.status in {"missing", "error"}]
    warnings = [result for result in results if result.status == "warning"]
    return 1 if failures or (warnings and not apply) else 0


if __name__ == "__main__":
    raise SystemExit(main())
