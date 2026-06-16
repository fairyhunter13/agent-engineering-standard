#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.canonical import STATE_DIR, STATE_FILE, dump_json, load_json  # noqa: E402


def _read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def _apply_scope(data: dict, payload: dict) -> None:
    session_id = payload.get("session_id")
    cwd = payload.get("cwd")
    if session_id:
        data["session_id"] = session_id
    if cwd:
        data["cwd"] = cwd


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
            "session_id": None,
            "cwd": None,
        },
    )


def mark_edit() -> int:
    payload = _read_payload()
    data = _load()
    _apply_scope(data, payload)
    data["pending_verification"] = True
    data["last_edit_at"] = int(time.time())
    _save(data)
    print("{}")
    return 0


def inspect_bash() -> int:
    payload = _read_payload()
    tool_input = payload.get("tool_input", {})
    command = tool_input.get("command") or tool_input.get("cmd") or tool_input.get("input") or ""
    data = _load()
    _apply_scope(data, payload)
    if "agent_engineering_standard_verified=1" in command.lower():
        data["pending_verification"] = False
        data["last_verified_command"] = command
        data["last_verified_at"] = int(time.time())
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
