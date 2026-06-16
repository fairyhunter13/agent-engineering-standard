from __future__ import annotations

from pathlib import Path

from policy.claude import (
    CLAUDE_DOCTRINE_END,
    CLAUDE_DOCTRINE_START,
    SHELL_LAUNCHER_START,
    claude_profiles,
    format_doctrine,
    managed_hook_commands,
    render_hooks,
    shell_launcher_body,
    skill_sources,
    skill_targets,
)
from policy.shared import HOME, read_text, replace_or_append_block, write_text
from scripts.audit_bash_aliases import audit_file
from scripts.install_common import ensure_managed_block, merge_hook_entries, manage_skill_link, manage_state_dir, result, diff_text


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
        results.append(
            ensure_managed_block(
                profile.config_root / "CLAUDE.md",
                start=CLAUDE_DOCTRINE_START,
                end=CLAUDE_DOCTRINE_END,
                body="\n".join(format_doctrine().splitlines()[1:-1]),
                label=f"claude({profile.name})/CLAUDE.md",
                apply=apply,
                dry_run=dry_run,
            )
        )
        results.append(
            merge_hook_entries(
                profile.config_root / "settings.json",
                rendered_hooks=render_hooks(repo_root),
                strip_commands=managed_hook_commands(repo_root),
                apply=apply,
                dry_run=dry_run,
                label=f"{profile.config_root.name}/settings.json hooks",
                missing_message="Claude hooks missing or drifted",
                configured_message="Claude hooks merged",
                synced_message="Claude hooks in sync",
            )
        )
    results.append(manage_state_dir(apply, dry_run))
    sources = skill_sources(repo_root)
    for profile in selected_profiles.values():
        for name, target in skill_targets(profile).items():
            results.append(manage_skill_link(target, sources[name], f"claude({profile.name})/skills/{name}", apply, dry_run))
    if include_shell:
        results.append(manage_shell(home / ".bash_aliases", apply, dry_run, adopt_legacy_shell_profiles))
    return results
