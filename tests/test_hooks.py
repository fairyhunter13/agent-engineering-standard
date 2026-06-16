from __future__ import annotations

import json
from pathlib import Path

from hooks import stop_verify, verification_state


def test_stop_verify_codex_blocks_with_current_contract(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True, "session_id": "sess-1"}))
    stop_verify.STATE_FILE = state_file
    capsys.readouterr()
    monkey_stdin = type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-1"})})()
    import sys
    original = sys.stdin
    sys.stdin = monkey_stdin
    try:
        assert stop_verify.main(["stop_verify.py", "codex"]) == 0
    finally:
        sys.stdin = original
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "Verification is still pending" in payload["reason"]


def test_stop_verify_ignores_pending_state_from_other_session(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True, "session_id": "sess-1"}))
    stop_verify.STATE_FILE = state_file
    capsys.readouterr()
    monkey_stdin = type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-2"})})()
    import sys
    original = sys.stdin
    sys.stdin = monkey_stdin
    try:
        assert stop_verify.main(["stop_verify.py", "codex"]) == 0
    finally:
        sys.stdin = original
    assert capsys.readouterr().out == ""


def test_stop_verify_claude_uses_stop_additional_context(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True}))
    stop_verify.STATE_FILE = state_file

    assert stop_verify.main(["stop_verify.py", "claude"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "Verification is still pending" in payload["hookSpecificOutput"]["additionalContext"]


def test_stop_verify_codex_allows_silently_when_not_pending(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": False}))
    stop_verify.STATE_FILE = state_file

    assert stop_verify.main(["stop_verify.py", "codex"]) == 0
    assert capsys.readouterr().out == ""


def test_verification_state_requires_explicit_marker(tmp_path: Path, monkeypatch, capsys) -> None:
    state_dir = tmp_path / "state"
    state_file = state_dir / "verification-state.json"
    monkeypatch.setattr(verification_state, "STATE_DIR", state_dir)
    monkeypatch.setattr(verification_state, "STATE_FILE", state_file)

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-1", "cwd": "/repo"})})(),
    )
    assert verification_state.mark_edit() == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is True
    assert state["session_id"] == "sess-1"
    assert state["cwd"] == "/repo"

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"tool_input": {"command": "pytest -q"}})})(),
    )
    assert verification_state.inspect_bash() == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is True
    assert state.get("last_verified_command") is None

    monkeypatch.setattr(
        "sys.stdin",
        type(
            "FakeStdin",
            (),
            {"read": lambda self: json.dumps({"tool_input": {"command": "AGENT_ENGINEERING_STANDARD_VERIFIED=1 pytest -q"}})},
        )(),
    )
    assert verification_state.inspect_bash() == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is False
    assert state["last_verified_command"] == "AGENT_ENGINEERING_STANDARD_VERIFIED=1 pytest -q"
