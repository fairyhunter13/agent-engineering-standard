from __future__ import annotations

from pathlib import Path

from policy.claude import (
    CLAUDE_DOCTRINE_END,
    CLAUDE_DOCTRINE_START,
    claude_profiles,
    format_doctrine,
    managed_hook_commands,
    render_hooks,
    skill_sources,
    skill_targets,
)
from policy.shared import HOME
from scripts.install_common import ensure_managed_block, merge_hook_entries, manage_skill_link, manage_state_dir


def install_claude(*, apply: bool, dry_run: bool, profiles: set[str], home: Path = HOME, repo_root: Path | None = None) -> list:
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
    return results
