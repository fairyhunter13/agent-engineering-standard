from __future__ import annotations

import json
from pathlib import Path

from scripts.install_policy import run_install


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_install_policy_apply_preserves_mcp_and_installs_managed_surfaces(tmp_path: Path) -> None:
    home = tmp_path
    repo_root = Path(__file__).resolve().parents[1]
    ose_block = """<!-- >>> opencode-search global instructions >>> -->
OSE
<!-- <<< opencode-search global instructions <<< -->
"""
    ose_agents = """[opencode-search-global-instructions:start]
OSE
[opencode-search-global-instructions:end]
"""
    for root in (home / ".claude", home / ".claude-account1", home / ".claude-account2"):
        _write(root / "CLAUDE.md", ose_block)
        _write(
            root / "settings.json",
            json.dumps(
                {
                    "mcpServers": {"opencode-search": {"type": "http", "url": "http://127.0.0.1:8765/mcp"}},
                    "other": True,
                }
            ),
        )
    _write(home / ".codex" / "AGENTS.md", ose_agents)
    _write(home / ".codex" / "config.toml", 'developer_instructions = "keep"\n')
    dot_claude_main = home / ".claude.json"
    dot_claude_main.write_text('{"mcpServers":{"opencode-search":{"type":"stdio"}}}')
    legacy_skill = home / ".claude" / "skills" / "lean-change"
    legacy_skill.mkdir(parents=True, exist_ok=True)
    (legacy_skill / "SKILL.md").write_text("legacy")

    results = run_install(
        apply=True,
        dry_run=False,
        targets={"claude", "codex", "skills", "hooks"},
        profiles={"main", "account1", "account2"},
        adopt_legacy_shell_profiles=False,
        home=home,
        repo_root=repo_root,
    )

    assert any(result.status == "configured" for result in results)
    main_claude = (home / ".claude" / "CLAUDE.md").read_text()
    assert "agent-engineering-standard:doctrine" in main_claude
    main_settings = json.loads((home / ".claude" / "settings.json").read_text())
    assert main_settings["mcpServers"]["opencode-search"]["url"] == "http://127.0.0.1:8765/mcp"
    assert main_settings["other"] is True
    assert (home / ".codex" / "config.toml").read_text() == 'developer_instructions = "keep"\n'
    assert dot_claude_main.read_text() == '{"mcpServers":{"opencode-search":{"type":"stdio"}}}'
    assert (home / ".claude" / "skills" / "lean-change").is_symlink()
    assert (home / ".codex" / "hooks.json").exists()
    assert (home / ".agents" / "skills" / "lean-change").is_symlink()
