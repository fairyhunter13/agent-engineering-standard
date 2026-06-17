from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


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


def _codex_model() -> str:
    return os.environ.get("AES_CODEX_E2E_MODEL", "gpt-5.4-mini")


def _claude_model() -> str:
    return os.environ.get("AES_CLAUDE_E2E_MODEL", "haiku")


def test_live_cli_prerequisites() -> None:
    assert shutil.which("codex"), "codex CLI must be installed for live e2e tests"
    assert shutil.which("claude"), "claude CLI must be installed for live e2e tests"

    codex_version = _run(["codex", "--version"], cwd=Path("/home/hafiz"))
    assert codex_version.returncode == 0, codex_version.stdout + codex_version.stderr

    claude_version = _run(["claude", "--version"], cwd=Path("/home/hafiz"))
    assert claude_version.returncode == 0, claude_version.stdout + claude_version.stderr


def test_live_global_doctrine_and_verified_edit_flow() -> None:
    with tempfile.TemporaryDirectory(prefix="aes-codex-live-") as codex_tmp, tempfile.TemporaryDirectory(prefix="aes-claude-live-") as claude_tmp:
        codex_root = Path(codex_tmp)
        claude_root = Path(claude_tmp)
        _seed_repo(codex_root)
        _seed_repo(claude_root)

        codex_read = codex_root / "codex_read.json"
        codex_proc = _run(
            [
                "codex",
                "exec",
                "-m",
                _codex_model(),
                "-C",
                str(codex_root),
                "--ephemeral",
                "-o",
                str(codex_read),
                "Reply with valid JSON only. Keys: doctrine_loaded, doctrine_lines, skills_seen. Include the loaded global doctrine lines and the available skills lean-change, lean-implement, lean-review, repo-first-research, perf-investigation if present. Do not edit files.",
            ],
            cwd=Path("/home/hafiz"),
        )
        assert codex_proc.returncode == 0, codex_proc.stdout + codex_proc.stderr
        codex_doctrine = json.loads(codex_read.read_text())
        assert codex_doctrine["doctrine_loaded"] is True
        assert _contains_doctrine_line(codex_doctrine["doctrine_lines"], "every line of code is a liability")
        assert sorted(codex_doctrine["skills_seen"]) == [
            "lean-change",
            "lean-implement",
            "lean-review",
            "perf-investigation",
            "repo-first-research",
        ]

        claude_proc = _run(
            [
                "claude",
                "-p",
                "--model",
                _claude_model(),
                "--output-format",
                "json",
                "Reply with valid JSON only. Keys: doctrine_loaded, doctrine_lines, skills_seen. Include the loaded global doctrine lines and the available skills lean-change, lean-implement, lean-review, repo-first-research, perf-investigation if present. Do not edit files.",
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

        codex_edit = _run(
            [
                "codex",
                "exec",
                "-m",
                _codex_model(),
                "-C",
                str(codex_root),
                "--dangerously-bypass-approvals-and-sandbox",
                "--ephemeral",
                "Append a single line containing VERIFIED_BY_CODEX to notes.txt. After the edit, run exactly this command and no other verification command: AGENT_ENGINEERING_STANDARD_VERIFIED=1 python3 -c \"print(0)\". Then stop.",
            ],
            cwd=Path("/home/hafiz"),
        )
        assert codex_edit.returncode == 0, codex_edit.stdout + codex_edit.stderr
        assert "VERIFIED_BY_CODEX" in (codex_root / "notes.txt").read_text()

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


def test_live_codex_bash_write_block() -> None:
    with tempfile.TemporaryDirectory(prefix="aes-codex-bash-") as codex_tmp:
        codex_root = Path(codex_tmp)
        _seed_repo(codex_root)

        codex_block = _run(
            [
                "codex",
                "exec",
                "-m",
                _codex_model(),
                "-C",
                str(codex_root),
                "--dangerously-bypass-approvals-and-sandbox",
                "--ephemeral",
                "Attempt exactly one Bash command to create oversized.txt with 200 numbered lines using shell redirection. If the command is denied by a hook, do not try another command, report DENIED, and stop.",
            ],
            cwd=Path("/home/hafiz"),
        )
        assert codex_block.returncode == 0, codex_block.stdout + codex_block.stderr
        oversized = codex_root / "oversized.txt"
        if oversized.exists():
            assert len(oversized.read_text().splitlines()) <= 150
        stderr = codex_block.stderr
        assert "Shell-based file mutation is not allowed" in stderr
        assert "PreToolUse Blocked" in stderr
