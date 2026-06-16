from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from policy.claude_profiles import ClaudeProfile, profile_manifest

REPO_NAME = "agent-engineering-standard"
REPO_ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
STATE_DIR = HOME / ".local" / "state" / REPO_NAME
STATE_FILE = STATE_DIR / "verification-state.json"

CLAUDE_DOCTRINE_START = "<!-- >>> agent-engineering-standard:doctrine >>> -->"
CLAUDE_DOCTRINE_END = "<!-- <<< agent-engineering-standard:doctrine <<< -->"
CODEX_DOCTRINE_START = "[agent-engineering-standard:doctrine:start]"
CODEX_DOCTRINE_END = "[agent-engineering-standard:doctrine:end]"
SHELL_LAUNCHER_START = "# >>> agent-engineering-standard:claude-launchers >>>"
SHELL_LAUNCHER_END = "# <<< agent-engineering-standard:claude-launchers <<<"

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

CLAUDE_LAUNCHER_COMMENT = """# Claude launchers (managed by agent-engineering-standard)
# Preserves the current shared-history multi-profile model.
function claude() {
    command claude --model "opusplan" --dangerously-skip-permissions "$@"
}

function claude1() {
    CLAUDE_CONFIG_DIR="$HOME/.claude-account1" claude "$@"
}

function claude2() {
    CLAUDE_CONFIG_DIR="$HOME/.claude-account2" claude "$@"
}"""

CLAUDE_SETTINGS_HOOKS = {
    "PreToolUse": [
        {
            "matcher": "Edit|Write|MultiEdit|NotebookEdit",
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/lean_gate.py"}],
        }
    ],
    "PostToolUse": [
        {
            "matcher": "Edit|Write|MultiEdit|NotebookEdit",
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/verification_state.py mark-edit"}],
        },
        {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/verification_state.py inspect-bash"}],
        },
    ],
    "Stop": [
        {
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/stop_verify.py claude"}],
        }
    ],
}

CODEX_HOOKS = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/lean_gate.py"}],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write|^apply_patch$",
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/verification_state.py mark-edit"}],
            },
            {
                "matcher": "^Bash$",
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/verification_state.py inspect-bash"}],
            },
        ],
        "Stop": [
            {
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/stop_verify.py codex"}],
            }
        ],
    }
}

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


def claude_profiles(home: Path | None = None) -> dict[str, ClaudeProfile]:
    return profile_manifest(home or HOME)


def format_claude_doctrine() -> str:
    return f"{CLAUDE_DOCTRINE_START}\n{DOCTRINE_BODY}\n{CLAUDE_DOCTRINE_END}\n"


def format_codex_doctrine() -> str:
    return f"{CODEX_DOCTRINE_START}\n{DOCTRINE_BODY}\n{CODEX_DOCTRINE_END}\n"


def format_shell_launcher_block() -> str:
    return f"{SHELL_LAUNCHER_START}\n{CLAUDE_LAUNCHER_COMMENT}\n{SHELL_LAUNCHER_END}\n"


def shell_launcher_body() -> str:
    return CLAUDE_LAUNCHER_COMMENT


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


def managed_hook_commands(repo_root: Path | None = None) -> set[str]:
    repo = str((repo_root or REPO_ROOT).resolve())
    commands = set()
    for event_entries in CLAUDE_SETTINGS_HOOKS.values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                commands.add(hook["command"].format(repo=repo))
    for event_entries in CODEX_HOOKS["hooks"].values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                commands.add(hook["command"].format(repo=repo))
    return commands


def render_claude_hooks(repo_root: Path | None = None) -> dict:
    repo = str((repo_root or REPO_ROOT).resolve())
    rendered: dict[str, list[dict]] = {}
    for event, entries in CLAUDE_SETTINGS_HOOKS.items():
        rendered[event] = []
        for entry in entries:
            new_entry = dict(entry)
            hooks = []
            for hook in entry.get("hooks", []):
                rendered_hook = dict(hook)
                rendered_hook["command"] = hook["command"].format(repo=repo)
                hooks.append(rendered_hook)
            new_entry["hooks"] = hooks
            rendered[event].append(new_entry)
    return rendered


def render_codex_hooks(repo_root: Path | None = None) -> dict:
    repo = str((repo_root or REPO_ROOT).resolve())
    rendered = {"hooks": {}}
    for event, entries in CODEX_HOOKS["hooks"].items():
        rendered["hooks"][event] = []
        for entry in entries:
            new_entry = dict(entry)
            hooks = []
            for hook in entry.get("hooks", []):
                rendered_hook = dict(hook)
                rendered_hook["command"] = hook["command"].format(repo=repo)
                hooks.append(rendered_hook)
            new_entry["hooks"] = hooks
            rendered["hooks"][event] = rendered["hooks"].get(event, []) + [new_entry]
    return rendered


def claude_skill_sources(agent: str, repo_root: Path | None = None) -> dict[str, Path]:
    base = (repo_root or REPO_ROOT) / "skills" / agent
    return {name: base / name for name in SKILL_NAMES}


def claude_skill_targets(profile: ClaudeProfile) -> dict[str, Path]:
    return {name: profile.config_root / "skills" / name for name in SKILL_NAMES}


def codex_skill_targets(home: Path | None = None) -> dict[str, Path]:
    root = (home or HOME) / ".agents" / "skills"
    return {name: root / name for name in SKILL_NAMES}


def symlink_points_to(path: Path, target: Path) -> bool:
    return path.is_symlink() and path.resolve() == target.resolve()


def replace_symlink(path: Path, target: Path, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)
    os.symlink(target, path)
