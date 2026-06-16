#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.canonical import STATE_DIR, STATE_FILE, dump_json, load_json, verification_hint  # noqa: E402


def _save(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(dump_json(data))


def _load() -> dict:
    return load_json(
        STATE_FILE,
        {
            "pending_verification": False,
            "last_edit_at": None,
            "last_verified_command": None,
            "last_verification_candidate": None,
        },
    )


def mark_edit() -> int:
    data = _load()
    data["pending_verification"] = True
    data["last_edit_at"] = int(time.time())
    _save(data)
    print("{}")
    return 0


def inspect_bash() -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input", {})
    command = tool_input.get("command") or tool_input.get("cmd") or tool_input.get("input") or ""
    data = _load()
    if verification_hint(command):
        data["last_verification_candidate"] = command
        data["last_verified_at"] = int(time.time())
    if "agent_engineering_standard_verified=1" in command.lower():
        data["pending_verification"] = False
        data["last_verified_command"] = command
    _save(data)
    print("{}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        raise SystemExit("usage: verification_state.py mark-edit|inspect-bash")
    if argv[1] == "mark-edit":
        return mark_edit()
    if argv[1] == "inspect-bash":
        return inspect_bash()
    raise SystemExit(f"unknown command: {argv[1]}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
