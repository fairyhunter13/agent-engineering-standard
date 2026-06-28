#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.worktree_clean import clean_worktrees  # noqa: E402


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}
    cwd = payload.get("cwd")
    removed = clean_worktrees(Path(cwd) if cwd else None)
    if removed:
        summary = f"Cleaned {len(removed)} stray agent worktree(s): {', '.join(removed)}"
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": summary}}))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
