from __future__ import annotations

from scripts.audit_bash_aliases import audit_text


def test_bash_alias_audit_detects_launchers_and_ignores_comment_reference() -> None:
    findings = audit_text(
        """
# comment mentioning claude-code
function claude() {
  command claude "$@"
}
alias claude1="CLAUDE_CONFIG_DIR=~/.claude-account1 claude"
alias claude2="CLAUDE_CONFIG_DIR=~/.claude-account2 claude"
"""
    )
    assert len(findings["launchers"]) == 3
    assert len(findings["shadowing"]) == 3
    assert any("claude-code" in item["text"] for item in findings["non_launcher_references"])
