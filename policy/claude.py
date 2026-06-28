from __future__ import annotations

from pathlib import Path

from policy.claude_profiles import ClaudeProfile, profile_manifest
from policy.shared import DOCTRINE_BODY, HOME, REPO_ROOT, SKILL_NAMES

CLAUDE_DOCTRINE_START = "<!-- >>> agent-engineering-standard:doctrine >>> -->"
CLAUDE_DOCTRINE_END = "<!-- <<< agent-engineering-standard:doctrine <<< -->"

CLAUDE_SETTINGS_HOOKS = {
    "PreToolUse": [
        {
            "matcher": "Edit|Write|MultiEdit|NotebookEdit",
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/claude/pre_tool_use.py"}],
        },
        {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/claude/pre_bash.py"}],
        }
    ],
    "PostToolUse": [
        {
            "matcher": "Edit|Write|MultiEdit|NotebookEdit",
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/claude/verification_state.py mark-edit"}],
        },
        {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/claude/verification_state.py inspect-bash"}],
        },
    ],
    "Stop": [
        {
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/claude/stop_verify.py"}],
        }
    ],
    "SessionStart": [
        {
            "hooks": [{"type": "command", "command": "python3 {repo}/hooks/claude/clean_worktrees.py"}],
        }
    ],
}

LEGACY_CLAUDE_HOOK_COMMANDS = (
    "python3 {repo}/hooks/lean_gate.py",
    "python3 {repo}/hooks/verification_state.py mark-edit",
    "python3 {repo}/hooks/verification_state.py inspect-bash",
    "python3 {repo}/hooks/stop_verify.py claude",
)


def claude_profiles(home: Path | None = None) -> dict[str, ClaudeProfile]:
    return profile_manifest(home or HOME)


def format_doctrine() -> str:
    return f"{CLAUDE_DOCTRINE_START}\n{DOCTRINE_BODY}\n{CLAUDE_DOCTRINE_END}\n"


def render_hooks(repo_root: Path | None = None) -> dict:
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


def managed_hook_commands(repo_root: Path | None = None) -> set[str]:
    repo = str((repo_root or REPO_ROOT).resolve())
    commands = set()
    for event_entries in render_hooks(repo_root).values():
        for entry in event_entries:
            for hook in entry.get("hooks", []):
                commands.add(hook["command"])
    commands.update(command.format(repo=repo) for command in LEGACY_CLAUDE_HOOK_COMMANDS)
    return commands


def skill_sources(repo_root: Path | None = None) -> dict[str, Path]:
    base = (repo_root or REPO_ROOT) / "skills" / "claude"
    return {name: base / name for name in SKILL_NAMES}


def skill_targets(profile: ClaudeProfile) -> dict[str, Path]:
    return {name: profile.config_root / "skills" / name for name in SKILL_NAMES}
