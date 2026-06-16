from __future__ import annotations

import json
from pathlib import Path

from hooks.claude import stop_verify as claude_stop_verify
from hooks.claude import verification_state as claude_verification_state
from hooks.codex import stop_verify as codex_stop_verify
from hooks.codex import verification_state as codex_verification_state
from hooks.core import evaluate_bash_guard


def test_stop_verify_codex_blocks_with_current_contract(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True, "session_id": "sess-1"}))
    codex_stop_verify.STATE_FILE = state_file
    capsys.readouterr()
    monkey_stdin = type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-1"})})()
    import sys
    original = sys.stdin
    sys.stdin = monkey_stdin
    try:
        assert codex_stop_verify.main() == 0
    finally:
        sys.stdin = original
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "block"
    assert "Verification is still pending" in payload["reason"]


def test_stop_verify_ignores_pending_state_from_other_session(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True, "session_id": "sess-1"}))
    codex_stop_verify.STATE_FILE = state_file
    capsys.readouterr()
    monkey_stdin = type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-2"})})()
    import sys
    original = sys.stdin
    sys.stdin = monkey_stdin
    try:
        assert codex_stop_verify.main() == 0
    finally:
        sys.stdin = original
    assert capsys.readouterr().out == ""


def test_stop_verify_claude_uses_stop_additional_context(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True}))
    claude_stop_verify.STATE_FILE = state_file

    assert claude_stop_verify.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "Verification is still pending" in payload["hookSpecificOutput"]["additionalContext"]


def test_stop_verify_codex_allows_silently_when_not_pending(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": False}))
    codex_stop_verify.STATE_FILE = state_file

    assert codex_stop_verify.main() == 0
    assert capsys.readouterr().out == ""


def test_verification_state_requires_explicit_marker(tmp_path: Path, monkeypatch, capsys) -> None:
    state_dir = tmp_path / "state"
    state_file = state_dir / "verification-state.json"
    monkeypatch.setattr(codex_verification_state, "STATE_DIR", state_dir)
    monkeypatch.setattr(codex_verification_state, "STATE_FILE", state_file)

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-1", "cwd": "/repo"})})(),
    )
    assert codex_verification_state.main(["verification_state.py", "mark-edit"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is True
    assert state["session_id"] == "sess-1"
    assert state["cwd"] == "/repo"

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"tool_input": {"command": "pytest -q"}})})(),
    )
    assert codex_verification_state.main(["verification_state.py", "inspect-bash"]) == 0
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
    assert codex_verification_state.main(["verification_state.py", "inspect-bash"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is False
    assert state["last_verified_command"] == "AGENT_ENGINEERING_STANDARD_VERIFIED=1 pytest -q"


def test_claude_and_codex_verification_state_share_logic(tmp_path: Path, monkeypatch, capsys) -> None:
    state_dir = tmp_path / "state"
    state_file = state_dir / "verification-state.json"
    monkeypatch.setattr(claude_verification_state, "STATE_DIR", state_dir)
    monkeypatch.setattr(claude_verification_state, "STATE_FILE", state_file)

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-2", "cwd": "/repo"})})(),
    )
    assert claude_verification_state.main(["verification_state.py", "mark-edit"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is True
    assert state["session_id"] == "sess-2"


def test_bash_guard_blocks_shell_write_to_source_like_file() -> None:
    allowed, reason = evaluate_bash_guard({"tool_input": {"command": "cat <<'EOF' > oversized.txt\n1\nEOF"}})
    assert allowed is False
    assert "Shell-based file mutation is not allowed" in reason


def test_bash_guard_allows_read_only_command() -> None:
    allowed, reason = evaluate_bash_guard({"tool_input": {"command": "pytest -q"}})
    assert allowed is True
    assert reason == ""


def test_bash_guard_allows_explicit_verification_command() -> None:
    allowed, reason = evaluate_bash_guard({"tool_input": {"command": "AGENT_ENGINEERING_STANDARD_VERIFIED=1 python3 -c \"print(0)\""}})
    assert allowed is True
    assert reason == ""
