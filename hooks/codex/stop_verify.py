#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.core import read_payload, scope_matches  # noqa: E402
from policy.shared import STATE_FILE, load_json  # noqa: E402


def main() -> int:
    payload = read_payload()
    data = load_json(STATE_FILE, {"pending_verification": False})
    if not data.get("pending_verification"):
        return 0
    if not scope_matches(data, payload):
        return 0
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": "Verification is still pending for the last edit. Run a relevant check before claiming completion (codex).",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
