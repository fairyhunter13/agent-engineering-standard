from __future__ import annotations

from policy.claude import (  # noqa: F401
    CLAUDE_DOCTRINE_END,
    CLAUDE_DOCTRINE_START,
    CLAUDE_SETTINGS_HOOKS,
    claude_profiles,
    format_doctrine as format_claude_doctrine,
    managed_hook_commands as claude_managed_hook_commands,
    render_hooks as render_claude_hooks,
    skill_sources as claude_skill_sources,
    skill_targets as claude_skill_targets,
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
    return claude_managed_hook_commands(repo_root)
