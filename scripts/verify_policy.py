#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.claude import render_hooks as render_claude_hooks  # noqa: E402
from policy.shared import HOME, Result  # noqa: E402
from scripts.audit_shell_aliases import verify_shell_aliases  # noqa: E402
from scripts.verify_claude import verify_claude  # noqa: E402


def _hook_payload(event: str, matcher: str) -> dict:
    base = {"session_id": "verify-claude", "cwd": "/tmp"}
    if event == "Stop":
        return base
    if "Bash" in matcher:
        return {**base, "tool_name": "Bash", "tool_input": {"command": 'AGENT_ENGINEERING_STANDARD_VERIFIED=1 python3 -c "print(0)"'}}
    return {**base, "tool_name": "Write", "tool_input": {"file_path": "/tmp/verify.txt", "content": "1\n"}}


def verify_hook_execution(repo_root: Path) -> Result:
    failures = []
    with tempfile.TemporaryDirectory(prefix="aes-hook-verify-") as tmp_home:
        env = dict(os.environ, HOME=tmp_home)
        surfaces = (("claude", render_claude_hooks(repo_root)),)
        for agent, hooks in surfaces:
            for event, entries in hooks.items():
                for entry in entries:
                    matcher = entry.get("matcher", "")
                    for hook in entry.get("hooks", []):
                        proc = subprocess.run(hook["command"], input=json.dumps(_hook_payload(event, matcher)), text=True, shell=True, capture_output=True, timeout=15, env=env)
                        if proc.returncode:
                            failures.append(f"{agent}/{event}/{matcher or '*'} exited {proc.returncode}")
    if failures:
        return Result("hook-execution", "error", "; ".join(failures))
    return Result("hook-execution", "already_ok", "Rendered hook commands execute successfully")


def verify_policy(home: Path = HOME, repo_root: Path | None = None) -> list[Result]:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: list[Result] = []
    results.extend(verify_claude(profiles={"main", "account1", "account2"}, home=home, repo_root=repo_root))
    results.append(verify_hook_execution(repo_root))
    results.append(verify_shell_aliases(home))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify global agent engineering policy install.")
    parser.add_argument("--json", action="store_true", dest="json_out")
    args = parser.parse_args()
    results = verify_policy()
    if args.json_out:
        print(json.dumps([result.__dict__ for result in results], indent=2))
    else:
        for result in results:
            print(f"[{result.status}] {result.tool}: {result.message}")
    failures = [result for result in results if result.status in {"missing", "error"}]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
