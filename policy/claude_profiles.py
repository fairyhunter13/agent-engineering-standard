from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClaudeProfile:
    name: str
    launcher: str
    config_root: Path


def profile_manifest(home: Path) -> dict[str, ClaudeProfile]:
    return {
        "main": ClaudeProfile("main", "claude", home / ".claude"),
        "account1": ClaudeProfile("account1", "claude1", home / ".claude-account1"),
        "account2": ClaudeProfile("account2", "claude2", home / ".claude-account2"),
    }
