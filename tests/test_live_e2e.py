from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

DOCTRINE_DISCOVERY_PROMPT = (
    "Reply with valid JSON only. Keys: doctrine_loaded, doctrine_lines, skills_seen. "
    "For doctrine_lines, copy the loaded agent-engineering-standard doctrine lines verbatim, including the exact line "
    "'- every line of code is a liability' if it is present. "
    "For skills_seen, include exactly these available skills when present: lean-change, lean-implement, lean-review, repo-first-research, perf-investigation. "
    "Do not edit files."
)


def _extract_json_blob(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped.removeprefix("```json").removesuffix("```").strip()
    return json.loads(stripped)


def _contains_doctrine_line(lines: list[str], needle: str) -> bool:
    return any(needle in line for line in lines)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=360)


def _seed_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
    (root / "notes.txt").write_text("seed\n")
    subprocess.run(["git", "add", "notes.txt"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", "init"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _claude_model() -> str:
    return os.environ.get("AES_CLAUDE_E2E_MODEL", "haiku")


def test_live_cli_prerequisites() -> None:
    assert shutil.which("claude"), "claude CLI must be installed for live e2e tests"

    claude_version = _run(["claude", "--version"], cwd=Path("/home/hafiz"))
    assert claude_version.returncode == 0, claude_version.stdout + claude_version.stderr


def test_live_claude_doctrine_and_verified_edit_flow() -> None:
    with tempfile.TemporaryDirectory(prefix="aes-claude-live-") as claude_tmp:
        claude_root = Path(claude_tmp)
        _seed_repo(claude_root)

        claude_proc = _run(
            [
                "claude",
                "-p",
                "--model",
                _claude_model(),
                "--output-format",
                "json",
                DOCTRINE_DISCOVERY_PROMPT,
            ],
            cwd=claude_root,
        )
        assert claude_proc.returncode == 0, claude_proc.stdout + claude_proc.stderr
        claude_result = json.loads(claude_proc.stdout)
        doctrine = _extract_json_blob(claude_result["result"])
        assert doctrine["doctrine_loaded"] is True
        assert _contains_doctrine_line(doctrine["doctrine_lines"], "every line of code is a liability")
        assert sorted(doctrine["skills_seen"]) == [
            "lean-change",
            "lean-implement",
            "lean-review",
            "perf-investigation",
            "repo-first-research",
        ]
        assert "claude-haiku-4-5" in json.dumps(claude_result.get("modelUsage", {}))

        claude_edit = _run(
            [
                "claude",
                "-p",
                "--model",
                _claude_model(),
                "--permission-mode",
                "bypassPermissions",
                "--output-format",
                "json",
                "Append a single line containing VERIFIED_BY_CLAUDE to notes.txt. After the edit, run exactly this command and no other verification command: AGENT_ENGINEERING_STANDARD_VERIFIED=1 python3 -c \"print(0)\". Then stop.",
            ],
            cwd=claude_root,
        )
        assert claude_edit.returncode == 0, claude_edit.stdout + claude_edit.stderr
        assert "VERIFIED_BY_CLAUDE" in (claude_root / "notes.txt").read_text()


def test_live_claude_bash_write_block() -> None:
    with tempfile.TemporaryDirectory(prefix="aes-claude-bash-") as claude_tmp:
        claude_root = Path(claude_tmp)
        _seed_repo(claude_root)

        claude_block = _run(
            [
                "claude",
                "-p",
                "--model",
                _claude_model(),
                "--permission-mode",
                "bypassPermissions",
                "--output-format",
                "json",
                "Using Bash only, create a file named oversized.txt containing 200 numbered lines, then stop without running verification.",
            ],
            cwd=claude_root,
        )
        assert claude_block.returncode == 0, claude_block.stdout + claude_block.stderr
        assert not (claude_root / "oversized.txt").exists()
        assert "permission_denials" in claude_block.stdout


def test_live_claude_stop_hook_terminates_without_loop() -> None:
    with tempfile.TemporaryDirectory(prefix="aes-claude-stop-") as tmp:
        root = Path(tmp)
        _seed_repo(root)
        proc = subprocess.run(
            [
                "claude",
                "-p",
                "--model",
                _claude_model(),
                "--permission-mode",
                "bypassPermissions",
                "--output-format",
                "json",
                "Write a file named stop_test.txt with exactly the text 'hello'. Do NOT run any bash command afterward. Stop immediately after the Write.",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert (root / "stop_test.txt").exists()


def test_live_claude_previously_protected_paths_now_allowed() -> None:
    """Writes to previously-protected paths (.env, secrets/) are now allowed by the hook."""
    with tempfile.TemporaryDirectory(prefix="aes-claude-protected-") as claude_tmp:
        claude_root = Path(claude_tmp)
        _seed_repo(claude_root)

        proc = _run(
            [
                "claude",
                "-p",
                "--model",
                _claude_model(),
                "--permission-mode",
                "bypassPermissions",
                "--output-format",
                "json",
                (
                    "Do the following two steps in order:\n"
                    "1. Use the Write tool to create a file named 'secrets/token.txt' containing exactly: SECRET_TOKEN\n"
                    "2. Use the Write tool to create a file named 'app.env' containing exactly: KEY=value\n"
                    "Then stop without running any verification command."
                ),
            ],
            cwd=claude_root,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        result = json.loads(proc.stdout)
        # Both files must exist — the hook no longer blocks them
        assert (claude_root / "secrets" / "token.txt").exists(), "secrets/token.txt was not created"
        assert "SECRET_TOKEN" in (claude_root / "secrets" / "token.txt").read_text()
        assert (claude_root / "app.env").exists(), "app.env was not created"
        assert "KEY=value" in (claude_root / "app.env").read_text()
        # No Edit/Write denial should appear in permission_denials
        denials = result.get("permission_denials", [])
        write_denials = [d for d in denials if isinstance(d, dict) and d.get("toolName", "") in ("Edit", "Write")]
        assert not write_denials, f"Unexpected write denials: {write_denials}"


def test_live_claude_write_guard_blocks_large_file() -> None:
    with tempfile.TemporaryDirectory(prefix="aes-claude-write-guard-") as tmp:
        root = Path(tmp)
        _seed_repo(root)
        proc = _run(
            [
                "claude",
                "-p",
                "--model",
                _claude_model(),
                "--permission-mode",
                "bypassPermissions",
                "--output-format",
                "json",
                "Use the Write tool to create large.txt with 200 numbered lines. Then stop.",
            ],
            cwd=root,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        large = root / "large.txt"
        if large.exists():
            assert len(large.read_text().splitlines()) <= 150
        assert "permission_denials" in proc.stdout
