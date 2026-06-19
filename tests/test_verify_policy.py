from __future__ import annotations

import json
from pathlib import Path

from scripts.install_policy import run_install
from scripts.audit_shell_aliases import audit_text, verify_shell_aliases
from scripts.verify_policy import verify_hook_execution, verify_policy


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
    for root in (home / ".claude", home / ".claude-account1", home / ".claude-account2"):
        _write(root / "CLAUDE.md", ose_block)
        _write(root / "settings.json", json.dumps({"mcpServers": {"opencode-search": {"type": "http", "url": "http://127.0.0.1:8765/mcp"}}}))

    run_install(
        apply=True,
        dry_run=False,
        targets={"claude", "skills", "hooks"},
        profiles={"main", "account1", "account2"},
        home=home,
        repo_root=repo_root,
    )

    results = verify_policy(home=home, repo_root=repo_root)
    failures = [result for result in results if result.status in {"missing", "error"}]
    assert not failures
    assert any(result.tool == "shell-alias-audit" and result.status == "already_ok" for result in results)


def test_shell_alias_audit_is_read_only_and_reports_stale_aes_block(tmp_path: Path) -> None:
    bash_aliases = tmp_path / ".bash_aliases"
    bash_aliases.write_text(
        "# >>> agent-engineering-standard:claude-launchers >>>\n"
        "function claude() { command claude \"$@\"; }\n"
        "# <<< agent-engineering-standard:claude-launchers <<<\n"
    )

    result = verify_shell_aliases(tmp_path)

    assert result.status == "warning"
    assert "no longer owns shell" in result.message
    assert bash_aliases.read_text().startswith("# >>> agent-engineering-standard")


def test_shell_alias_audit_detects_external_launchers_without_warning() -> None:
    findings = audit_text(
        """
function claude() {
  command claude "$@"
}
alias claude1="CLAUDE_CONFIG_DIR=~/.claude-account1 claude"
"""
    )

    assert findings["aes_managed_block_present"] is False
    assert len(findings["claude_launcher_definitions"]) == 2


def test_verify_hook_execution_runs_rendered_commands() -> None:
    result = verify_hook_execution(Path(__file__).resolve().parents[1])

    assert result.status == "already_ok"
