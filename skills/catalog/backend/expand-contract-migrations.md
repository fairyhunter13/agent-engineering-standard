---
name: expand-contract-migrations
description: Perform zero-downtime database schema changes using the expand-contract (parallel-change) pattern.
discipline: backend
tags: [database, migrations, zero-downtime, schema, postgresql]
---

# Expand-Contract Database Migrations

## When to use

Renaming columns, changing column types, splitting or merging columns, or removing columns on a
live production database without downtime. When a schema change would otherwise require coordinating
an application deploy simultaneously with a migration — creating a window where the old app reads a
column that no longer exists, or the new app reads a column that doesn't yet exist.

## Signal

- Migration requires an exclusive table lock that blocks reads and writes for the duration of the
  ALTER operation on a large table.
- A column rename in one deploy breaks the old version of the application that is still running
  alongside the new version during a rolling deploy.
- "Deploy window" required — teams schedule maintenance downtime for schema changes.
- Application code and DB schema must be deployed simultaneously or the app crashes.
- `ALTER TABLE … DROP COLUMN` in a migration that runs before all app instances have been updated.

## Why

In a rolling deployment, old and new versions of the application code run simultaneously on
different pods for a window of 30 seconds to several minutes. If a migration drops or renames a
column, old pods reading the old column name break immediately. The expand-contract pattern
eliminates this coupling by decoupling schema changes from application changes across multiple
deploys.

Additionally, `ALTER TABLE` on large tables in PostgreSQL (pre-14 for some operations) or MySQL
takes an exclusive lock for the full duration, blocking all reads and writes. `CREATE INDEX
CONCURRENTLY` and pt-online-schema-change avoid this, but require the expand-contract approach for
column changes.

## Remediate

The expand-contract pattern has five discrete phases. Each phase is a separate deploy.

**Phase 1 — Expand: add the new column.**
```sql
ALTER TABLE users ADD COLUMN email_address VARCHAR(255);
```
The new column is nullable. No application code change yet. No lock contention on most DBs for
adding a nullable column.

**Phase 2 — Dual-write: application writes to both old and new columns; reads from old.**
Deploy application code that:
- Writes to both `email` (old) and `email_address` (new) on insert/update.
- Reads from `email` (old) — the new column is not yet authoritative.
This ensures new rows have both columns populated.

**Phase 3 — Backfill: populate the new column for existing rows.**
Run a batched background job (not a single large UPDATE) to avoid table locks:
```sql
UPDATE users
SET email_address = email
WHERE email_address IS NULL AND id BETWEEN :start AND :end;
```
Run in batches of 1,000–10,000 rows with a small delay between batches to avoid I/O saturation.

**Phase 4 — Migrate reads: application reads from the new column.**
Deploy application code that now reads from `email_address`. Both columns are still written.
Monitor for nulls in `email_address` — any NULLs indicate a backfill gap. Add a NOT NULL
constraint after confirming no NULLs:
```sql
ALTER TABLE users ALTER COLUMN email_address SET NOT NULL;
```

**Phase 5 — Contract: remove the old column.**
Only after no running version of the application reads the old column:
```sql
ALTER TABLE users DROP COLUMN email;
```
For Postgres: use `ALTER TABLE … DROP COLUMN` — it is fast and only takes a brief lock in modern
versions. For MySQL on large tables: use `pt-online-schema-change` or `gh-ost`.

**Never combine phases into a single deploy.** Each phase must be independently deployable and
independently rollback-safe.

## References

- Martin Fowler — Parallel Change pattern (martinfowler.com)
- Shopify Engineering Blog: Zero-downtime migrations
- Percona: pt-online-schema-change tool
- GitHub: gh-ost (online schema change for MySQL)
- PostgreSQL documentation: ALTER TABLE locking behavior
