#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from policy.shared import HOME, Result  # noqa: E402
from scripts.install_claude import install_claude  # noqa: E402

ALL_TARGETS = {"claude", "skills", "hooks"}
DEFAULT_TARGETS = {"claude", "skills", "hooks"}


def run_install(
    *,
    apply: bool,
    dry_run: bool,
    targets: set[str],
    profiles: set[str],
    home: Path = HOME,
    repo_root: Path | None = None,
) -> list[Result]:
    repo_root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    results: list[Result] = []
    if targets & {"claude", "skills", "hooks"}:
        results.extend(
            install_claude(
                apply=apply,
                dry_run=dry_run,
                profiles=profiles,
                home=home,
                repo_root=repo_root,
            )
        )
    return results


def parse_targets(value: str) -> set[str]:
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    invalid = parsed - ALL_TARGETS
    if invalid:
        raise argparse.ArgumentTypeError(f"Unknown targets: {sorted(invalid)}")
    return parsed or set(DEFAULT_TARGETS)


def parse_profiles(value: str) -> set[str]:
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    valid = {"main", "account1", "account2"}
    invalid = parsed - valid
    if invalid:
        raise argparse.ArgumentTypeError(f"Unknown profiles: {sorted(invalid)}")
    return parsed or valid


def main() -> int:
    parser = argparse.ArgumentParser(description="Install global agent engineering policy surfaces.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", dest="json_out", action="store_true")
    parser.add_argument("--targets", type=parse_targets, default=set(DEFAULT_TARGETS))
    parser.add_argument("--profiles", type=parse_profiles, default={"main", "account1", "account2"})
    args = parser.parse_args()
    results = run_install(
        apply=args.apply,
        dry_run=args.dry_run,
        targets=args.targets,
        profiles=args.profiles,
    )
    if args.json_out:
        print(json.dumps([result.__dict__ for result in results], indent=2))
    else:
        for result in results:
            print(f"[{result.status}] {result.tool}: {result.message}")
    failures = [result for result in results if result.status in {"missing", "error"}]
    warnings = [result for result in results if result.status == "warning"]
    return 1 if failures or (warnings and not args.apply) else 0


if __name__ == "__main__":
    raise SystemExit(main())
