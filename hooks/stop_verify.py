#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.canonical import load_json, STATE_FILE  # noqa: E402


def _codex_ok() -> int:
    return 0


def _claude_ok() -> int:
    print("{}")
    return 0


def main(argv: list[str]) -> int:
    tool = argv[1] if len(argv) > 1 else "agent"
    data = load_json(STATE_FILE, {"pending_verification": False})
    if not data.get("pending_verification"):
        return _codex_ok() if tool == "codex" else _claude_ok()
    candidate = data.get("last_verification_candidate")
    message = f"Verification is still pending for the last edit. Run a relevant check before claiming completion ({tool})."
    if candidate:
        message = (
            "A possible verification command was seen, but the hook does not treat repository-specific checks as authoritative. "
            f"Confirm the relevant verification explicitly before claiming completion ({tool}). Last candidate: {candidate}"
        )
    if tool == "codex":
        print(
            json.dumps(
                {
                    "continue": False,
                    "stopReason": "verification pending",
                    "systemMessage": message,
                }
            )
        )
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": message,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
