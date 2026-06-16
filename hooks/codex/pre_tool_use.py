#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.core import emit_json, evaluate_edit_guard, read_payload  # noqa: E402


def main() -> int:
    payload = read_payload()
    if not payload:
        return emit_json(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Hook input was not valid JSON.",
                }
            }
        )
    allowed, reason = evaluate_edit_guard(payload)
    if allowed:
        return 0
    return emit_json(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
