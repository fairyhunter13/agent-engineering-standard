from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from hooks.claude import stop_verify as claude_stop_verify
from hooks.claude import verification_state as claude_verification_state
from hooks.core import evaluate_bash_guard, evaluate_edit_guard


def test_stop_verify_allows_when_scope_mismatches(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True, "session_id": "sess-1"}))
    claude_stop_verify.STATE_FILE = state_file
    capsys.readouterr()
    monkey_stdin = type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-2"})})()
    original = sys.stdin
    sys.stdin = monkey_stdin
    try:
        assert claude_stop_verify.main() == 0
    finally:
        sys.stdin = original
    assert json.loads(capsys.readouterr().out) == {}


def test_stop_verify_allows_when_stop_hook_active(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True, "session_id": "sess-1"}))
    claude_stop_verify.STATE_FILE = state_file
    capsys.readouterr()
    monkey_stdin = type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-1", "stop_hook_active": True})})()
    original = sys.stdin
    sys.stdin = monkey_stdin
    try:
        assert claude_stop_verify.main() == 0
    finally:
        sys.stdin = original
    assert json.loads(capsys.readouterr().out) == {}


def test_stop_verify_claude_uses_stop_additional_context(tmp_path: Path, capsys) -> None:
    state_file = tmp_path / "verification-state.json"
    state_file.write_text(json.dumps({"pending_verification": True}))
    claude_stop_verify.STATE_FILE = state_file

    assert claude_stop_verify.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "Stop"
    assert "Verification is still pending" in payload["hookSpecificOutput"]["additionalContext"]


def test_verification_state_clears_after_verification_command(tmp_path: Path, monkeypatch, capsys) -> None:
    state_dir = tmp_path / "state"
    state_file = state_dir / "verification-state.json"
    monkeypatch.setattr(claude_verification_state, "STATE_DIR", state_dir)
    monkeypatch.setattr(claude_verification_state, "STATE_FILE", state_file)

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-1", "cwd": "/repo"})})(),
    )
    assert claude_verification_state.main(["verification_state.py", "mark-edit"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is True
    assert state["session_id"] == "sess-1"
    assert state["cwd"] == "/repo"

    monkeypatch.setattr(
        "sys.stdin",
        type(
            "FakeStdin",
            (),
            {
                "read": lambda self: json.dumps(
                    {"tool_input": {"command": "sed -n '1,80p' hooks/core.py"}, "tool_response": "Process exited with code 0"}
                )
            },
        )(),
    )
    assert claude_verification_state.main(["verification_state.py", "inspect-bash"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is True
    assert state.get("last_verified_command") is None

    monkeypatch.setattr(
        "sys.stdin",
        type(
            "FakeStdin",
            (),
            {
                "read": lambda self: json.dumps(
                    {"tool_input": {"command": "python3 scripts/verify_policy.py"}, "tool_response": "Process exited with code 0"}
                )
            },
        )(),
    )
    assert claude_verification_state.main(["verification_state.py", "inspect-bash"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is False
    assert state["last_verified_command"] == "python3 scripts/verify_policy.py"


def test_verification_state_clears_when_tool_response_absent(tmp_path: Path, monkeypatch, capsys) -> None:
    """tool_response may be absent; verification command should still clear pending."""
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

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"tool_input": {"command": "python3 scripts/verify_policy.py"}})})(),
    )
    assert claude_verification_state.main(["verification_state.py", "inspect-bash"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is False
    assert state["last_verified_command"] == "python3 scripts/verify_policy.py"


def test_verification_state_stays_pending_on_explicit_failure(tmp_path: Path, monkeypatch, capsys) -> None:
    """A verification command with non-zero exit code must not clear pending."""
    state_dir = tmp_path / "state"
    state_file = state_dir / "verification-state.json"
    monkeypatch.setattr(claude_verification_state, "STATE_DIR", state_dir)
    monkeypatch.setattr(claude_verification_state, "STATE_FILE", state_file)

    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"session_id": "sess-3", "cwd": "/repo"})})(),
    )
    assert claude_verification_state.main(["verification_state.py", "mark-edit"]) == 0
    capsys.readouterr()

    monkeypatch.setattr(
        "sys.stdin",
        type(
            "FakeStdin",
            (),
            {"read": lambda self: json.dumps({"tool_input": {"command": "python3 scripts/verify_policy.py"}, "tool_response": "Process exited with code 1"})},
        )(),
    )
    assert claude_verification_state.main(["verification_state.py", "inspect-bash"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is True
    assert state.get("last_verified_command") is None


def test_verification_state_marks_pending_on_edit(tmp_path: Path, monkeypatch, capsys) -> None:
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


def test_verification_state_recovers_corrupt_state_file(tmp_path: Path, monkeypatch, capsys) -> None:
    state_dir = tmp_path / "state"
    state_file = state_dir / "verification-state.json"
    state_dir.mkdir()
    state_file.write_text('{"pending_verification": false}\n{"broken": true}\n')
    monkeypatch.setattr(claude_verification_state, "STATE_DIR", state_dir)
    monkeypatch.setattr(claude_verification_state, "STATE_FILE", state_file)
    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: json.dumps({"tool_input": {"command": "pytest -q"}})})(),
    )

    assert claude_verification_state.main(["verification_state.py", "inspect-bash"]) == 0
    capsys.readouterr()
    state = json.loads(state_file.read_text())
    assert state["pending_verification"] is False


def test_bash_guard_blocks_shell_write_to_source_like_file() -> None:
    allowed, reason = evaluate_bash_guard({"tool_input": {"command": "cat <<'EOF' > oversized.txt\n1\nEOF"}})
    assert allowed is False
    assert "Shell-based file mutation is not allowed" in reason


def test_bash_guard_allows_read_only_command() -> None:
    allowed, reason = evaluate_bash_guard({"tool_input": {"command": "pytest -q"}})
    assert allowed is True
    assert reason == ""


def test_bash_guard_allows_read_only_python_heredoc() -> None:
    allowed, reason = evaluate_bash_guard({"tool_input": {"command": "python3 - <<'PY'\nprint('ok')\nPY"}})
    assert allowed is True
    assert reason == ""


def test_bash_guard_allows_explicit_verification_command() -> None:
    allowed, reason = evaluate_bash_guard({"tool_input": {"command": "AGENT_ENGINEERING_STANDARD_VERIFIED=1 python3 -c \"print(0)\""}})
    assert allowed is True
    assert reason == ""


def test_edit_guard_blocks_large_new_file(tmp_path: Path) -> None:
    target = tmp_path / "new_module.py"
    content = "".join(f"line {i}\n" for i in range(1, 201))
    allowed, reason = evaluate_edit_guard({"tool_name": "Write", "tool_input": {"file_path": str(target), "content": content}})
    assert allowed is False
    assert "exceeds 150" in reason


def test_edit_guard_blocks_large_net_change_for_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "existing.py"
    target.write_text("seed\n")
    new_text = "".join(f"line {i}\n" for i in range(1, 42))
    allowed, reason = evaluate_edit_guard({"tool_name": "Edit", "tool_input": {"file_path": str(target), "old_string": "", "new_string": new_text}})
    assert allowed is False
    assert "exceeds 40" in reason


def test_edit_guard_allows_small_change(tmp_path: Path) -> None:
    target = tmp_path / "existing.py"
    target.write_text("seed\n")
    allowed, reason = evaluate_edit_guard({"tool_name": "Edit", "tool_input": {"file_path": str(target), "old_string": "seed", "new_string": "seed updated"}})
    assert allowed is True
    assert reason == ""


def test_post_tool_state_writes_tolerate_concurrent_processes(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    payload = json.dumps(
        {
            "session_id": "sess-1",
            "cwd": str(tmp_path),
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "notes.txt"), "content": "1\n"},
        }
    )
    procs = [
        subprocess.Popen(
            [sys.executable, str(repo_root / "hooks/claude/verification_state.py"), "mark-edit"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        for _ in range(20)
    ]

    results = [proc.communicate(payload, timeout=10) + (proc.returncode,) for proc in procs]
    failures = [stderr for _stdout, stderr, returncode in results if returncode != 0]
    assert not failures
    state_file = tmp_path / ".local/state/agent-engineering-standard/verification-state.json"
    assert json.loads(state_file.read_text())["pending_verification"] is True
