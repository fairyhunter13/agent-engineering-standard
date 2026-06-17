#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.claude import (
    CLAUDE_DOCTRINE_END,
    CLAUDE_DOCTRINE_START,
    claude_profiles,
    managed_hook_commands as claude_managed_hook_commands,
    skill_sources as claude_skill_sources,
    skill_targets as claude_skill_targets,
)
from policy.codex import CODEX_DOCTRINE_END, CODEX_DOCTRINE_START, hooks_path as codex_hooks_path, skill_sources as codex_skill_sources, skill_targets as codex_skill_targets
from policy.shared import HOME, STATE_DIR, dump_json, load_json, remove_block, write_text


def uninstall_claude(*, dry_run: bool) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    commands = claude_managed_hook_commands(repo_root)
    sources = claude_skill_sources(repo_root)
    for profile in claude_profiles().values():
        path = profile.config_root / "CLAUDE.md"
        write_text(path, remove_block(path.read_text() if path.exists() else "", CLAUDE_DOCTRINE_START, CLAUDE_DOCTRINE_END), dry_run=dry_run)
        settings_path = profile.config_root / "settings.json"
        data = load_json(settings_path, {})
        hooks = dict(data.get("hooks", {}))
        for event, entries in list(hooks.items()):
            kept = []
            for entry in entries:
                filtered = [hook for hook in entry.get("hooks", []) if hook.get("command") not in commands]
                if filtered:
                    kept.append({**entry, "hooks": filtered})
            if kept:
                hooks[event] = kept
            else:
                hooks.pop(event, None)
        data["hooks"] = hooks
        write_text(settings_path, dump_json(data), dry_run=dry_run)
        for name, target in claude_skill_targets(profile).items():
            if target.is_symlink() and target.resolve() == sources[name].resolve() and not dry_run:
                target.unlink()


def uninstall_codex(*, dry_run: bool) -> None:
    agents_path = HOME / ".codex" / "AGENTS.md"
    write_text(agents_path, remove_block(agents_path.read_text() if agents_path.exists() else "", CODEX_DOCTRINE_START, CODEX_DOCTRINE_END), dry_run=dry_run)
    hooks_path = codex_hooks_path(HOME)
    if hooks_path.exists() and not dry_run:
        hooks_path.unlink()
    sources = codex_skill_sources()
    for name, target in codex_skill_targets().items():
        if target.is_symlink() and target.resolve() == sources[name].resolve() and not dry_run:
            target.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove agent-engineering-standard owned surfaces.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    uninstall_claude(dry_run=args.dry_run)
    uninstall_codex(dry_run=args.dry_run)
    if STATE_DIR.exists() and not args.dry_run:
        for child in STATE_DIR.glob("*"):
            child.unlink()
        STATE_DIR.rmdir()
    print(json.dumps({"status": "ok"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
