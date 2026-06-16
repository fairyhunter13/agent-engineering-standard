#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.canonical import SHELL_LAUNCHER_END, SHELL_LAUNCHER_START

LAUNCHER_NAMES = {"claude", "claude1", "claude2"}


def _block_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start = text.find(SHELL_LAUNCHER_START)
    end = text.find(SHELL_LAUNCHER_END)
    if start != -1 and end != -1 and end > start:
        ranges.append((start, end + len(SHELL_LAUNCHER_END)))
    return ranges


def _inside_managed(offset: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= offset <= end for start, end in ranges)


def audit_text(text: str) -> dict:
    managed_ranges = _block_ranges(text)
    findings = {
        "launchers": [],
        "non_launcher_references": [],
        "duplicates": [],
        "shadowing": [],
        "conflicts": [],
    }
    defs_by_name: dict[str, list[dict]] = {}
    for match in re.finditer(r"^(alias\s+(\w+)=.*|function\s+(\w+)\s*\(\)\s*\{|(\w+)\s*\(\)\s*\{)", text, re.MULTILINE):
        line = text.count("\n", 0, match.start()) + 1
        raw = match.group(1)
        name = match.group(2) or match.group(3) or match.group(4)
        body = raw
        kind = "alias" if raw.startswith("alias ") else "function"
        managed = _inside_managed(match.start(), managed_ranges)
        mentions_claude = (
            name in LAUNCHER_NAMES
            or "CLAUDE_CONFIG_DIR=" in body
            or re.search(r"\bclaude\b", body)
        )
        if mentions_claude:
            record = {"name": name, "kind": kind, "line": line, "managed": managed, "text": raw.strip()}
            defs_by_name.setdefault(name, []).append(record)
            if name in LAUNCHER_NAMES or "CLAUDE_CONFIG_DIR=" in body or re.search(r"\bclaude\b", body):
                findings["launchers"].append(record)
    for name, defs in defs_by_name.items():
        if len(defs) > 1:
            findings["duplicates"].append({"name": name, "definitions": defs})
        if name in LAUNCHER_NAMES and any(not item["managed"] for item in defs):
            unmanaged = [item for item in defs if not item["managed"]]
            findings["shadowing"].append({"name": name, "definitions": unmanaged})
            findings["conflicts"].append({"name": name, "definitions": unmanaged})
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if "claude" not in stripped.lower():
            continue
        if stripped.startswith("alias claude") or stripped.startswith("function claude") or stripped.startswith("claude()"):
            continue
        if "claude1" in stripped or "claude2" in stripped:
            continue
        if "claude-code" in stripped.lower() or stripped.startswith("#"):
            findings["non_launcher_references"].append({"line": lineno, "text": stripped})
    return findings


def audit_file(path: Path) -> dict:
    return audit_text(path.read_text() if path.exists() else "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit ~/.bash_aliases for Claude launchers.")
    parser.add_argument("--path", default=str(Path.home() / ".bash_aliases"))
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args()
    findings = audit_file(Path(args.path))
    if args.json_out:
        print(json.dumps(findings, indent=2))
    else:
        print(json.dumps(findings, indent=2))
    return 1 if findings["shadowing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
