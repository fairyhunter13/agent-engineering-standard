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
    dot_claude_main = home / ".claude.json"
    dot_claude_main.write_text('{"mcpServers":{"opencode-search":{"type":"stdio"}}}')
    legacy_skill = home / ".claude" / "skills" / "lean-change"
    legacy_skill.mkdir(parents=True, exist_ok=True)
    (legacy_skill / "SKILL.md").write_text("legacy")

    results = run_install(
        apply=True,
        dry_run=False,
        targets={"claude", "skills", "hooks"},
        profiles={"main", "account1", "account2"},
        home=home,
        repo_root=repo_root,
    )

    assert any(result.status == "configured" for result in results)
    main_claude = (home / ".claude" / "CLAUDE.md").read_text()
    assert "agent-engineering-standard:doctrine" in main_claude
    main_settings = json.loads((home / ".claude" / "settings.json").read_text())
    assert main_settings["mcpServers"]["opencode-search"]["url"] == "http://127.0.0.1:8765/mcp"
    assert main_settings["other"] is True
    all_commands = [
        hook["command"]
        for entries in main_settings["hooks"].values()
        for entry in entries
        for hook in entry.get("hooks", [])
    ]
    assert "python3 /home/hafiz/git/github.com/fairyhunter13/agent-engineering-standard/hooks/lean_gate.py" not in all_commands
    assert dot_claude_main.read_text() == '{"mcpServers":{"opencode-search":{"type":"stdio"}}}'
    assert (home / ".claude" / "skills" / "lean-change").is_symlink()
    # SessionStart hook must be registered for worktree auto-clean
    session_start_hooks = main_settings["hooks"].get("SessionStart", [])
    session_start_commands = [h["command"] for entry in session_start_hooks for h in entry.get("hooks", [])]
    assert any("clean_worktrees" in cmd for cmd in session_start_commands)
