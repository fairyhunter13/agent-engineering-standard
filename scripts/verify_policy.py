#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.codex import hooks_path  # noqa: E402
from policy.shared import HOME, Result  # noqa: E402
from scripts.verify_claude import verify_claude  # noqa: E402
from scripts.verify_codex import verify_codex  # noqa: E402


def verify_policy(home: Path = HOME, repo_root: Path | None = None) -> list[Result]:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: list[Result] = []
    results.extend(verify_claude(profiles={"main", "account1", "account2"}, home=home, repo_root=repo_root))
    results.extend(verify_codex(home=home, repo_root=repo_root))
    results.append(Result("codex-hook-trust", "warning", "Codex hooks.json is installed, but manual trust review in /hooks is still required", str(hooks_path(home))))
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
