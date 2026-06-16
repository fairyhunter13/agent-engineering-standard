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
    SHELL_LAUNCHER_END,
    SHELL_LAUNCHER_START,
    claude_profiles,
    managed_hook_commands as claude_managed_hook_commands,
)
from policy.codex import CODEX_DOCTRINE_END, CODEX_DOCTRINE_START, hooks_path as codex_hooks_path
from policy.shared import HOME, STATE_DIR, dump_json, load_json, remove_block, write_text


def uninstall_claude(*, dry_run: bool) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    commands = claude_managed_hook_commands(repo_root)
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
        skills_dir = profile.config_root / "skills"
        if skills_dir.exists():
            for target in skills_dir.glob("*"):
                if target.is_symlink() and not dry_run:
                    target.unlink()
    bash_aliases = HOME / ".bash_aliases"
    write_text(bash_aliases, remove_block(bash_aliases.read_text() if bash_aliases.exists() else "", SHELL_LAUNCHER_START, SHELL_LAUNCHER_END), dry_run=dry_run)


def uninstall_codex(*, dry_run: bool) -> None:
    agents_path = HOME / ".codex" / "AGENTS.md"
    write_text(agents_path, remove_block(agents_path.read_text() if agents_path.exists() else "", CODEX_DOCTRINE_START, CODEX_DOCTRINE_END), dry_run=dry_run)
    hooks_path = codex_hooks_path(HOME)
    if hooks_path.exists() and not dry_run:
        hooks_path.unlink()
    skills_dir = HOME / ".agents" / "skills"
    if skills_dir.exists():
        for target in skills_dir.glob("*"):
            if target.is_symlink() and not dry_run:
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
