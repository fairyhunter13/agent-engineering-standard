#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROTECTED_MARKERS = ("/secrets/", "/.local/share/opencode-search/", "/GoogleDrive/", "/OneDrive/")
UNGATED_MARKERS = ("/.claude/", "/.codex/", "/.agents/skills/", "/.local/state/agent-engineering-standard/")
VERIFICATION_MARKER = "agent_engineering_standard_verified=1"


def emit_json(payload: dict) -> int:
    print(json.dumps(payload))
    return 0


def read_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def line_count(text: str) -> int:
    return 0 if not text else len(text.splitlines())


def evaluate_edit_guard(payload: dict) -> tuple[bool, str]:
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or ""
    if any(marker in file_path for marker in UNGATED_MARKERS):
        return True, ""
    if any(marker in file_path for marker in PROTECTED_MARKERS) or file_path.endswith(".env"):
        return False, f"Protected path: {file_path}"
    tool_name = payload.get("tool_name", "")
    if tool_name == "MultiEdit":
        new_text = "\n".join(edit.get("new_string", "") for edit in tool_input.get("edits", []))
        old_text = "\n".join(edit.get("old_string", "") for edit in tool_input.get("edits", []))
    elif tool_name == "NotebookEdit":
        new_text = tool_input.get("new_source", "")
        old_text = tool_input.get("old_source", "")
    else:
        new_text = tool_input.get("new_string") or tool_input.get("content") or ""
        old_text = tool_input.get("old_string", "")
    abs_path = Path(file_path) if file_path.startswith("/") else Path.cwd() / file_path
    is_new_file = not abs_path.exists()
    added = line_count(new_text)
    removed = line_count(old_text)
    net = added - removed
    if is_new_file and added > 150:
        return False, f"New file too large: {added} lines exceeds 150."
    if not is_new_file and net > 40:
        return False, f"Diff too large: +{net} net lines exceeds 40."
    return True, ""


def load_state(load_json_fn, state_file: Path) -> dict:
    return load_json_fn(
        state_file,
        {
            "pending_verification": False,
            "last_edit_at": None,
            "last_verified_command": None,
            "session_id": None,
            "cwd": None,
        },
    )


def apply_scope(data: dict, payload: dict) -> None:
    session_id = payload.get("session_id")
    cwd = payload.get("cwd")
    if session_id:
        data["session_id"] = session_id
    if cwd:
        data["cwd"] = cwd


def save_state(state_dir: Path, state_file: Path, dump_json_fn, data: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file.write_text(dump_json_fn(data))


def mark_edit(state_dir: Path, state_file: Path, load_json_fn, dump_json_fn) -> int:
    payload = read_payload()
    data = load_state(load_json_fn, state_file)
    apply_scope(data, payload)
    data["pending_verification"] = True
    data["last_edit_at"] = int(time.time())
    save_state(state_dir, state_file, dump_json_fn, data)
    print("{}")
    return 0


def inspect_bash(state_dir: Path, state_file: Path, load_json_fn, dump_json_fn) -> int:
    payload = read_payload()
    tool_input = payload.get("tool_input", {})
    command = tool_input.get("command") or tool_input.get("cmd") or tool_input.get("input") or ""
    data = load_state(load_json_fn, state_file)
    apply_scope(data, payload)
    if VERIFICATION_MARKER in command.lower():
        data["pending_verification"] = False
        data["last_verified_command"] = command
        data["last_verified_at"] = int(time.time())
    save_state(state_dir, state_file, dump_json_fn, data)
    print("{}")
    return 0


def scope_matches(data: dict, payload: dict) -> bool:
    stored_session = data.get("session_id")
    current_session = payload.get("session_id")
    if stored_session and current_session:
        return stored_session == current_session
    stored_cwd = data.get("cwd")
    current_cwd = payload.get("cwd")
    if stored_cwd and current_cwd:
        return stored_cwd == current_cwd
    return True
