from __future__ import annotations

import json
from pathlib import Path

from scripts.install_policy import run_install
from scripts.verify_policy import verify_policy


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_verify_policy_reports_installed_state_and_keeps_ose_surfaces(tmp_path: Path) -> None:
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
        _write(root / "settings.json", json.dumps({"mcpServers": {"opencode-search": {"type": "http", "url": "http://127.0.0.1:8765/mcp"}}}))
    _write(home / ".codex" / "AGENTS.md", ose_agents)
    _write(home / ".codex" / "config.toml", 'model = "gpt-5.4"\n')

    run_install(
        apply=True,
        dry_run=False,
        targets={"claude", "codex", "skills", "hooks"},
        profiles={"main", "account1", "account2"},
        home=home,
        repo_root=repo_root,
    )

    results = verify_policy(home=home, repo_root=repo_root)
    failures = [result for result in results if result.status in {"missing", "error"}]
    assert not failures
    assert any(result.tool == "codex-hook-trust" and result.status == "warning" for result in results)
