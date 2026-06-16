from __future__ import annotations

from policy.claude import (  # noqa: F401
    CLAUDE_DOCTRINE_END,
    CLAUDE_DOCTRINE_START,
    CLAUDE_LAUNCHER_COMMENT,
    CLAUDE_SETTINGS_HOOKS,
    SHELL_LAUNCHER_END,
    SHELL_LAUNCHER_START,
    claude_profiles,
    format_doctrine as format_claude_doctrine,
    format_shell_launcher_block,
    managed_hook_commands as claude_managed_hook_commands,
    render_hooks as render_claude_hooks,
    shell_launcher_body,
    skill_sources as claude_skill_sources,
    skill_targets as claude_skill_targets,
)
from policy.codex import (  # noqa: F401
    CODEX_DOCTRINE_END,
    CODEX_DOCTRINE_START,
    CODEX_HOOKS,
    agents_path as codex_agents_path,
    format_doctrine as format_codex_doctrine,
    hooks_path as codex_hooks_path,
    managed_hook_commands as codex_managed_hook_commands,
    render_hooks as render_codex_hooks,
    skill_sources as codex_skill_sources,
    skill_targets as codex_skill_targets,
)
from policy.shared import (  # noqa: F401
    DOCTRINE_BODY,
    DOCTRINE_LINES,
    HOME,
    REPO_NAME,
    REPO_ROOT,
    Result,
    STATE_DIR,
    STATE_FILE,
    SKILL_NAMES,
    dump_json,
    ensure_directory,
    load_json,
    read_text,
    remove_block,
    replace_or_append_block,
    replace_symlink,
    symlink_points_to,
    write_text,
)


def managed_hook_commands(repo_root=None) -> set[str]:
    return claude_managed_hook_commands(repo_root) | codex_managed_hook_commands(repo_root)
