from __future__ import annotations

from pathlib import Path

from policy.shared import HOME
from scripts.install_codex import install_codex


def verify_codex(*, home: Path = HOME, repo_root: Path | None = None) -> list:
    return install_codex(
        apply=False,
        dry_run=False,
        home=home,
        repo_root=repo_root,
    )
