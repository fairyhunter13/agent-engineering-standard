from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.install_policy import run_install

OSE_REPO = Path("/home/hafiz/git/github.com/fairyhunter13/opencode-search-engine")
sys.path.insert(0, str(OSE_REPO / "scripts"))
from integrations.canonical import (  # noqa: E402
    CANONICAL_BODY,
    CANONICAL_MCP_URL,
    SENTINEL_AGENTS_END,
    SENTINEL_AGENTS_START,
    SENTINEL_CLAUDE_END,
    SENTINEL_CLAUDE_START,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _replace_sentinel_block(text: str, start: str, end: str, new_body: str) -> str:
    si = text.find(start)
    ei = text.find(end)
    if si == -1 or ei == -1 or ei < si:
        trimmed = text.rstrip()
        prefix = f"{trimmed}\n\n" if trimmed else ""
        return f"{prefix}{start}\n{new_body}\n{end}\n"
    return text[:si] + start + "\n" + new_body + "\n" + end + text[ei + len(end):]


def _apply_ose_surfaces(home: Path) -> None:
    for root in (home / ".claude", home / ".claude-account1", home / ".claude-account2"):
        current = (root / "CLAUDE.md").read_text() if (root / "CLAUDE.md").exists() else ""
        _write(
            root / "CLAUDE.md",
            _replace_sentinel_block(current, SENTINEL_CLAUDE_START, SENTINEL_CLAUDE_END, CANONICAL_BODY),
        )
        settings = json.loads((root / "settings.json").read_text()) if (root / "settings.json").exists() else {}
        settings.setdefault("mcpServers", {})["opencode-search"] = {"type": "http", "url": CANONICAL_MCP_URL}
        _write(root / "settings.json", json.dumps(settings, indent=2) + "\n")

    agents_path = home / ".codex" / "AGENTS.md"
    current_agents = agents_path.read_text() if agents_path.exists() else ""
    _write(
        agents_path,
        _replace_sentinel_block(current_agents, SENTINEL_AGENTS_START, SENTINEL_AGENTS_END, CANONICAL_BODY),
    )
    config_path = home / ".codex" / "config.toml"
    old_config = config_path.read_text() if config_path.exists() else ""
    ose_block = '\n[mcp_servers.opencode-search]\nurl = "http://127.0.0.1:8765/mcp"\n'
    if "[mcp_servers.opencode-search]" not in old_config:
        _write(config_path, old_config.rstrip() + ose_block)


def _assert_aes_and_ose_both_present(home: Path) -> None:
    for root in (home / ".claude", home / ".claude-account1", home / ".claude-account2"):
        md = (root / "CLAUDE.md").read_text()
        assert "agent-engineering-standard:doctrine" in md
        assert SENTINEL_CLAUDE_START in md
        settings = json.loads((root / "settings.json").read_text())
        assert settings["mcpServers"]["opencode-search"]["url"] == CANONICAL_MCP_URL
        commands = [
            hook["command"]
            for entries in settings["hooks"].values()
            for entry in entries
            for hook in entry.get("hooks", [])
        ]
        assert any("/hooks/claude/pre_tool_use.py" in command for command in commands)

    # OSE manages ~/.codex surfaces; AES must not overwrite or delete them
    agents = (home / ".codex" / "AGENTS.md").read_text()
    assert SENTINEL_AGENTS_START in agents
    assert CANONICAL_MCP_URL in (home / ".codex" / "config.toml").read_text()


def _seed_blank_home(home: Path) -> None:
    for root in (home / ".claude", home / ".claude-account1", home / ".claude-account2"):
        _write(root / "CLAUDE.md", "")
        _write(root / "settings.json", "{}\n")
    _write(home / ".codex" / "AGENTS.md", "")
    _write(home / ".codex" / "config.toml", 'developer_instructions = "keep"\n')


def test_ose_then_aes_preserves_both_owned_surfaces(tmp_path: Path) -> None:
    home = tmp_path
    repo_root = Path(__file__).resolve().parents[1]
    _seed_blank_home(home)
    _apply_ose_surfaces(home)

    run_install(
        apply=True,
        dry_run=False,
        targets={"claude", "skills", "hooks"},
        profiles={"main", "account1", "account2"},
        home=home,
        repo_root=repo_root,
    )

    _assert_aes_and_ose_both_present(home)


def test_aes_then_ose_preserves_both_owned_surfaces(tmp_path: Path) -> None:
    home = tmp_path
    repo_root = Path(__file__).resolve().parents[1]
    _seed_blank_home(home)

    run_install(
        apply=True,
        dry_run=False,
        targets={"claude", "skills", "hooks"},
        profiles={"main", "account1", "account2"},
        home=home,
        repo_root=repo_root,
    )
    _apply_ose_surfaces(home)

    _assert_aes_and_ose_both_present(home)
