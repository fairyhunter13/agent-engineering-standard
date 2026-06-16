from __future__ import annotations

from pathlib import Path

from policy.shared import DOCTRINE_BODY, HOME, REPO_ROOT, SKILL_NAMES

CODEX_DOCTRINE_START = "[agent-engineering-standard:doctrine:start]"
CODEX_DOCTRINE_END = "[agent-engineering-standard:doctrine:end]"

CODEX_HOOKS = {
    "hooks": {
        "PreToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/codex/pre_tool_use.py"}],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Edit|Write|^apply_patch$",
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/codex/verification_state.py mark-edit"}],
            },
            {
                "matcher": "^Bash$",
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/codex/verification_state.py inspect-bash"}],
            },
        ],
        "Stop": [
            {
                "hooks": [{"type": "command", "command": "python3 {repo}/hooks/codex/stop_verify.py"}],
            }
        ],
    }
}


def format_doctrine() -> str:
    return f"{CODEX_DOCTRINE_START}\n{DOCTRINE_BODY}\n{CODEX_DOCTRINE_END}\n"


def agents_path(home: Path | None = None) -> Path:
    return (home or HOME) / ".codex" / "AGENTS.md"


def hooks_path(home: Path | None = None) -> Path:
    return (home or HOME) / ".codex" / "hooks.json"


def render_hooks(repo_root: Path | None = None) -> dict:
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


def managed_hook_commands(repo_root: Path | None = None) -> set[str]:
    commands = set()
    for event_entries in render_hooks(repo_root)["hooks"].values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                commands.add(hook["command"])
    return commands


def skill_sources(repo_root: Path | None = None) -> dict[str, Path]:
    base = (repo_root or REPO_ROOT) / "skills" / "codex"
    return {name: base / name for name in SKILL_NAMES}


def skill_targets(home: Path | None = None) -> dict[str, Path]:
    root = (home or HOME) / ".agents" / "skills"
    return {name: root / name for name in SKILL_NAMES}
