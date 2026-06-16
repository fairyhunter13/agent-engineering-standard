#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from hooks.core import inspect_bash, mark_edit  # noqa: E402
from policy.shared import STATE_DIR, STATE_FILE, dump_json, load_json  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("usage: verification_state.py mark-edit|inspect-bash")
    if argv[1] == "mark-edit":
        return mark_edit(STATE_DIR, STATE_FILE, load_json, dump_json)
    if argv[1] == "inspect-bash":
        return inspect_bash(STATE_DIR, STATE_FILE, load_json, dump_json)
    raise SystemExit(f"unknown command: {argv[1]}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
