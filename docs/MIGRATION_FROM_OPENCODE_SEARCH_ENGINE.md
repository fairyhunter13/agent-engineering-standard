# Migration From opencode-search-engine

`agent-engineering-standard` becomes the global owner of generic doctrine, hook wiring, and skills.

Sequence:

1. Run `python3 scripts/install_policy.py --apply --adopt-legacy-shell-profiles`.
2. Run `python3 scripts/verify_policy.py`.
3. Run `python3 scripts/migrate_from_opencode_search_engine.py --apply-cleanup`.

Safety rule:

- never remove OSE lean ownership before the new owner is verified live across all Claude profiles and global Codex

Cleanup scope:

- remove legacy lean sentinel blocks from `~/.claude/*/CLAUDE.md` and `~/.codex/AGENTS.md`
- reduce OSE ownership in `scripts/integrations/canonical.py`
- reduce OSE ownership in `scripts/configure_integrations.py`

Non-goals in v1:

- no MCP rewrites
- no `.claude.json` rewrites
- no `~/.codex/config.toml` rewrites for hooks
- no shell profile management
