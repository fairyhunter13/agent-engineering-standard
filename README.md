# agent-engineering-standard

Global doctrine, hooks, skills, and Claude launcher management for Claude and Codex.

This repo owns the generic engineering standard:
- doctrine blocks for `~/.claude/*/CLAUDE.md` and `~/.codex/AGENTS.md`
- generic Claude/Codex hook wiring
- generic Claude/Codex skills
- migration of generic lean ownership out of `opencode-search-engine`

This repo does not own:
- OSE MCP config
- OSE prompt sentinel blocks
- OSE Codex `developer_instructions`
- shell profile management

Primary commands:

```bash
python3 scripts/install_policy.py --check
python3 scripts/install_policy.py --apply --adopt-legacy-shell-profiles
python3 scripts/verify_policy.py
python3 scripts/migrate_from_opencode_search_engine.py --apply
python3 scripts/migrate_from_opencode_search_engine.py --apply-cleanup
```

Live behavior tests require working `codex` and `claude` CLIs and fail if either setup is unavailable:

```bash
pytest -q tests/test_live_e2e.py
```
