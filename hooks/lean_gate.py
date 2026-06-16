#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROTECTED_MARKERS = ("/secrets/", "/.local/share/opencode-search/", "/GoogleDrive/", "/OneDrive/")
UNGATED_MARKERS = ("/.claude/", "/.codex/", "/.agents/skills/", "/.local/state/agent-engineering-standard/")


def _emit(payload: dict) -> int:
    print(json.dumps(payload))
    return 0


def _allow() -> int:
    return 0


def _deny(reason: str) -> int:
    return _emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def _line_count(text: str) -> int:
    return 0 if not text else len(text.splitlines())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return _deny("Hook input was not valid JSON.")
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path") or ""
    if any(marker in file_path for marker in UNGATED_MARKERS):
        return _allow()
    if any(marker in file_path for marker in PROTECTED_MARKERS) or file_path.endswith(".env"):
        return _deny(f"Protected path: {file_path}")
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
    added = _line_count(new_text)
    removed = _line_count(old_text)
    net = added - removed
    if is_new_file and added > 150:
        return _deny(f"New file too large: {added} lines exceeds 150.")
    if not is_new_file and net > 40:
        return _deny(f"Diff too large: +{net} net lines exceeds 40.")
    return _allow()


if __name__ == "__main__":
    raise SystemExit(main())
