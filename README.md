# agent-engineering-standard

Global doctrine, hooks, and skills for Claude.

This repo owns the generic engineering standard:
- doctrine blocks for `~/.claude/*/CLAUDE.md`
- generic Claude hook wiring
- generic Claude skills
- migration of generic lean ownership out of `opencode-search-engine`

This repo does not own:
- OSE MCP config
- OSE prompt sentinel blocks
- OSE Codex `developer_instructions`
- shell profile management

Primary commands:

```bash
python3 scripts/install_policy.py --check
python3 scripts/install_policy.py --apply
python3 scripts/verify_policy.py
python3 scripts/migrate_from_opencode_search_engine.py --apply
python3 scripts/migrate_from_opencode_search_engine.py --apply-cleanup
```

Live behavior tests require a working `claude` CLI and fail if it is unavailable:

```bash
pytest -q tests/test_live_e2e.py
```
