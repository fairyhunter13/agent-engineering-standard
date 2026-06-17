#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.shared import HOME, Result  # noqa: E402

AES_SHELL_START = "# >>> agent-engineering-standard:claude-launchers >>>"
AES_SHELL_END = "# <<< agent-engineering-standard:claude-launchers <<<"
CLAUDE_LAUNCHERS = {"claude", "claude1", "claude2"}


def audit_text(text: str) -> dict:
    definitions = []
    for match in re.finditer(r"^(alias\s+(\w+)=.*|function\s+(\w+)\s*\(\)\s*\{|(\w+)\s*\(\)\s*\{)", text, re.MULTILINE):
        name = match.group(2) or match.group(3) or match.group(4)
        raw = match.group(1).strip()
        if name in CLAUDE_LAUNCHERS or "CLAUDE_CONFIG_DIR=" in raw or re.search(r"\bclaude\b", raw):
            definitions.append(
                {
                    "name": name,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "text": raw,
                }
            )
    return {
        "aes_managed_block_present": AES_SHELL_START in text or AES_SHELL_END in text,
        "claude_launcher_definitions": definitions,
    }


def audit_file(path: Path) -> dict:
    return audit_text(path.read_text() if path.exists() else "")


def verify_shell_aliases(home: Path = HOME) -> Result:
    path = home / ".bash_aliases"
    findings = audit_file(path)
    if findings["aes_managed_block_present"]:
        return Result("shell-alias-audit", "warning", "Stale AES shell launcher block exists; AES no longer owns shell profile management", str(path))
    count = len(findings["claude_launcher_definitions"])
    if count:
        return Result("shell-alias-audit", "already_ok", f"Read-only audit found {count} Claude launcher definition(s); shell remains externally owned", str(path))
    return Result("shell-alias-audit", "already_ok", "No Claude shell launcher definitions found", str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only audit for Claude launcher definitions in shell aliases.")
    parser.add_argument("--path", default=str(HOME / ".bash_aliases"))
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args()
    findings = audit_file(Path(args.path))
    print(json.dumps(findings, indent=2) if args.json_out else json.dumps(findings, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
