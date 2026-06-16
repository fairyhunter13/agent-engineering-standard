from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

REPO_NAME = "agent-engineering-standard"
REPO_ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
STATE_DIR = HOME / ".local" / "state" / REPO_NAME
STATE_FILE = STATE_DIR / "verification-state.json"

DOCTRINE_LINES = (
    "- every line of code is a liability",
    "- prefer no change, then deletion, then the smallest sufficient diff",
    "- correctness before speed",
    "- first-contact repo research is mandatory",
    "- reuse existing repo patterns before inventing abstractions",
    "- performance changes require evidence",
    "- verification is required before completion",
    "- repo-specific guidance overrides this global doctrine when more specific",
)
DOCTRINE_BODY = "\n".join(DOCTRINE_LINES)

SKILL_NAMES = (
    "lean-change",
    "repo-first-research",
    "lean-implement",
    "lean-review",
    "perf-investigation",
)


@dataclass
class Result:
    tool: str
    status: str
    message: str
    path: str = ""
    diff: str = ""


def replace_or_append_block(text: str, start: str, end: str, body: str) -> str:
    si = text.find(start)
    ei = text.find(end)
    if si == -1 or ei == -1 or ei < si:
        trimmed = text.rstrip()
        prefix = f"{trimmed}\n\n" if trimmed else ""
        return f"{prefix}{start}\n{body}\n{end}\n"
    return text[:si] + start + "\n" + body + "\n" + end + text[ei + len(end):]


def remove_block(text: str, start: str, end: str) -> str:
    si = text.find(start)
    ei = text.find(end)
    if si == -1 or ei == -1 or ei < si:
        return text
    tail = text[ei + len(end):]
    while tail.startswith("\n"):
        tail = tail[1:]
    head = text[:si].rstrip()
    if head and tail:
        return head + "\n\n" + tail
    if head:
        return head + "\n"
    return tail


def ensure_directory(path: Path, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def write_text(path: Path, content: str, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return dict(default or {})
    text = path.read_text().strip()
    if not text:
        return dict(default or {})
    return json.loads(text)


def dump_json(data: dict) -> str:
    return json.dumps(data, indent=2, sort_keys=False) + "\n"


def symlink_points_to(path: Path, target: Path) -> bool:
    return path.is_symlink() and path.resolve() == target.resolve()


def replace_symlink(path: Path, target: Path, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.exists():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    os.symlink(target, path)
