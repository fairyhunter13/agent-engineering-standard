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

## Engineering skill catalogue (June 2026)

**Two-tier architecture:**

| Tier | What | Token cost | How loaded |
|------|------|-----------|------------|
| Native (6 skills) | `lean-change`, `lean-implement`, `lean-review`, `repo-first-research`, `perf-investigation`, **`engineering-skill-catalog`** | ~6 descriptions at session start | Symlinked into all 3 profiles by `install_policy.py` |
| RAG catalogue (86+ skills) | `skills/catalog/{backend,frontend,infra,qa,security,data,craft}/*.md` | Zero startup cost | Retrieved on demand via OSE MCP `search`/`ask` |

The dispatcher skill `engineering-skill-catalog` tells Claude to call `mcp__opencode-search__search` for any specialized engineering task (N+1 queries, SLOs, OWASP, canary deploys, contract testing, etc.). OSE (shared daemon at `127.0.0.1:8765`, already wired into all 3 profiles) embeds and reranks the catalogue.

**First-time index (explicit, one-time):**

```bash
ocs index /home/hafiz/git/github.com/fairyhunter13/agent-engineering-standard
```

The file watcher keeps the index fresh after that. The `.opencode-index.yaml` scopes indexing to `skills/catalog/` only.

**Apply skill symlinks to all profiles:**

```bash
python3 scripts/install_policy.py --apply
```

**Catalogue tests:**

```bash
# Corpus + install gate (deterministic, no GPU required)
pytest -q tests/test_catalog_e2e.py -k "not live"

# Full live suite (GPU + OSE daemon + claude CLI required)
pytest -q tests/test_catalog_e2e.py -m live
```
