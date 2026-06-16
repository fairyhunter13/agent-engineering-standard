#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.canonical import HOME, remove_block  # noqa: E402
from scripts.install_policy import run_install  # noqa: E402
from scripts.verify_policy import verify_policy  # noqa: E402

OSE_REPO = Path("/home/hafiz/git/github.com/fairyhunter13/opencode-search-engine")
OSE_LEAN_CLAUDE_START = "<!-- >>> lean-change mandate >>> -->"
OSE_LEAN_CLAUDE_END = "<!-- <<< lean-change mandate <<< -->"
OSE_LEAN_AGENTS_START = "[lean-change-mandate:start]"
OSE_LEAN_AGENTS_END = "[lean-change-mandate:end]"


def _cleanup_live_prompts(dry_run: bool) -> None:
    for path in (
        HOME / ".claude" / "CLAUDE.md",
        HOME / ".claude-account1" / "CLAUDE.md",
        HOME / ".claude-account2" / "CLAUDE.md",
    ):
        text = path.read_text() if path.exists() else ""
        path.write_text(remove_block(text, OSE_LEAN_CLAUDE_START, OSE_LEAN_CLAUDE_END)) if not dry_run else None
    agents = HOME / ".codex" / "AGENTS.md"
    text = agents.read_text() if agents.exists() else ""
    if not dry_run:
        agents.write_text(remove_block(text, OSE_LEAN_AGENTS_START, OSE_LEAN_AGENTS_END))


def _cleanup_ose_files(dry_run: bool) -> None:
    canonical_path = OSE_REPO / "scripts" / "integrations" / "canonical.py"
    configure_path = OSE_REPO / "scripts" / "configure_integrations.py"
    markers = (
        "LEAN_GATE_HOOK_PATH",
        "SENTINEL_LEAN_START",
        "SENTINEL_LEAN_END",
        "SENTINEL_LEAN_AGENTS_START",
        "SENTINEL_LEAN_AGENTS_END",
        "LEAN_BODY",
        "def lean_claude_block()",
        "def lean_agents_block()",
        "LEAN_SKILL_MD",
    )
    canonical_text = canonical_path.read_text() if canonical_path.exists() else ""
    configure_text = configure_path.read_text() if configure_path.exists() else ""
    leftovers = [marker for marker in markers if marker in canonical_text or marker in configure_text]
    if leftovers:
        raise RuntimeError(f"OSE lean ownership markers still present: {', '.join(leftovers)}")


def _new_owner_live() -> bool:
    results = verify_policy()
    return not any(result.status in {"missing", "error"} for result in results if not result.tool.startswith("ose-"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate generic lean ownership out of opencode-search-engine.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--apply-cleanup", action="store_true")
    args = parser.parse_args()

    if args.apply:
        results = run_install(
            apply=True,
            dry_run=False,
            targets={"claude", "codex", "skills", "hooks"},
            profiles={"main", "account1", "account2"},
            adopt_legacy_shell_profiles=True,
        )
        ok = _new_owner_live()
        print(json.dumps({"installed": [result.__dict__ for result in results], "new_owner_live": ok}, indent=2))
        return 0 if ok else 1

    if args.apply_cleanup:
        if not _new_owner_live():
            print(json.dumps({"error": "new owner not live; refusing cleanup"}, indent=2))
            return 1
        _cleanup_live_prompts(dry_run=False)
        _cleanup_ose_files(dry_run=False)
        print(json.dumps({"status": "cleanup-complete"}, indent=2))
        return 0

    status = {
        "new_repo_present": Path(__file__).resolve().parents[1].exists(),
        "ose_repo_present": OSE_REPO.exists(),
        "new_owner_live": _new_owner_live(),
    }
    try:
        _cleanup_ose_files(dry_run=True)
        status["ose_lean_cleanup_complete"] = True
    except RuntimeError as exc:
        status["ose_lean_cleanup_complete"] = False
        status["ose_cleanup_error"] = str(exc)
    print(json.dumps(status, indent=2))
    return 0 if status["new_repo_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
