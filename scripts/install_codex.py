from __future__ import annotations

from pathlib import Path

from policy.codex import CODEX_DOCTRINE_END, CODEX_DOCTRINE_START, agents_path, format_doctrine, hooks_path, render_hooks, skill_sources, skill_targets
from policy.shared import HOME, dump_json, read_text, replace_or_append_block, write_text
from scripts.install_common import diff_text, manage_skill_link, result


def ensure_doctrine(path: Path, apply: bool, dry_run: bool) -> object:
    old = read_text(path)
    new = replace_or_append_block(old, CODEX_DOCTRINE_START, CODEX_DOCTRINE_END, "\n".join(format_doctrine().splitlines()[1:-1]))
    if old == new:
        return result("codex/AGENTS.md", "already_ok", "Doctrine block in sync", path)
    if not apply:
        return result("codex/AGENTS.md", "missing", "Doctrine block missing or drifted", path, diff_text(old, new, str(path)))
    write_text(path, new, dry_run=dry_run)
    return result("codex/AGENTS.md", "configured", "Doctrine block updated", path, diff_text(old, new, str(path)))


def manage_hooks(path: Path, repo_root: Path, apply: bool, dry_run: bool) -> object:
    old_text = read_text(path)
    new_text = dump_json(render_hooks(repo_root))
    if old_text.strip() == new_text.strip():
        return result("codex/hooks.json", "already_ok", "Codex hooks in sync", path)
    if not apply:
        return result("codex/hooks.json", "missing", "Codex hooks missing or drifted", path, diff_text(old_text, new_text, str(path)))
    write_text(path, new_text, dry_run=dry_run)
    return result("codex/hooks.json", "configured", "Codex hooks installed", path, diff_text(old_text, new_text, str(path)))


def install_codex(*, apply: bool, dry_run: bool, home: Path = HOME, repo_root: Path | None = None) -> list:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: list = []
    results.append(ensure_doctrine(agents_path(home), apply, dry_run))
    results.append(manage_hooks(hooks_path(home), repo_root, apply, dry_run))
    sources = skill_sources(repo_root)
    for name, target in skill_targets(home).items():
        results.append(manage_skill_link(target, sources[name], f"codex-skills/{name}", apply, dry_run))
    return results
