from __future__ import annotations

from pathlib import Path

from policy.shared import HOME
from scripts.install_claude import install_claude


def verify_claude(*, profiles: set[str], home: Path = HOME, repo_root: Path | None = None) -> list:
    return install_claude(
        apply=False,
        dry_run=False,
        profiles=profiles,
        home=home,
        repo_root=repo_root,
    )
