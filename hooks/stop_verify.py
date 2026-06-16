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


def _read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _scope_matches(data: dict, payload: dict) -> bool:
    stored_session = data.get("session_id")
    current_session = payload.get("session_id")
    if stored_session and current_session:
        return stored_session == current_session
    stored_cwd = data.get("cwd")
    current_cwd = payload.get("cwd")
    if stored_cwd and current_cwd:
        return stored_cwd == current_cwd
    return True


def main(argv: list[str]) -> int:
    tool = argv[1] if len(argv) > 1 else "agent"
    payload = _read_payload()
    data = load_json(STATE_FILE, {"pending_verification": False})
    if not data.get("pending_verification"):
        return _codex_ok() if tool == "codex" else _claude_ok()
    if not _scope_matches(data, payload):
        return _codex_ok() if tool == "codex" else _claude_ok()
    message = f"Verification is still pending for the last edit. Run a relevant check before claiming completion ({tool})."
    if tool == "codex":
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": message,
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
