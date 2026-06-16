from __future__ import annotations

from pathlib import Path

from policy.codex import CODEX_DOCTRINE_END, CODEX_DOCTRINE_START, agents_path, format_doctrine, hooks_path, render_hooks, skill_sources, skill_targets
from policy.shared import HOME
from scripts.install_common import ensure_managed_block, manage_owned_json, manage_skill_link


def install_codex(*, apply: bool, dry_run: bool, home: Path = HOME, repo_root: Path | None = None) -> list:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: list = []
    results.append(
        ensure_managed_block(
            agents_path(home),
            start=CODEX_DOCTRINE_START,
            end=CODEX_DOCTRINE_END,
            body="\n".join(format_doctrine().splitlines()[1:-1]),
            label="codex/AGENTS.md",
            apply=apply,
            dry_run=dry_run,
        )
    )
    results.append(
        manage_owned_json(
            hooks_path(home),
            rendered=render_hooks(repo_root),
            apply=apply,
            dry_run=dry_run,
            label="codex/hooks.json",
            missing_message="Codex hooks missing or drifted",
            configured_message="Codex hooks installed",
            synced_message="Codex hooks in sync",
        )
    )
    sources = skill_sources(repo_root)
    for name, target in skill_targets(home).items():
        results.append(manage_skill_link(target, sources[name], f"codex-skills/{name}", apply, dry_run))
    return results
