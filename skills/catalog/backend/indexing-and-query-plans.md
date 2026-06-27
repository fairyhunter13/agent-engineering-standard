---
name: indexing-and-query-plans
description: Diagnose and fix slow queries by adding missing indexes, rewriting query shapes, and validating execution plans.
discipline: backend
tags: [database, sql, indexes, performance, query-plans]
---

# Indexing and Query Plan Analysis

## When to use

Slow-query log surfaces queries taking >100 ms in production; autovacuum is not keeping up with
write load; full table scans appear on tables with more than a few thousand rows; an endpoint's
latency degrades as data grows.

## Signal

- `EXPLAIN ANALYZE` (Postgres) or `EXPLAIN FORMAT=JSON` (MySQL) shows `Seq Scan` on a large table
  where a filter or join condition is present.
- `rows=` estimate in the plan diverges significantly from `actual rows=` — indicates stale
  statistics; run `ANALYZE`.
- `Buffers: shared hit=0 read=N` with large N — disk I/O dominating because data is not cached.
- Slow-query log shows the same query template appearing repeatedly with runtimes >100 ms.
- DB CPU is consistently high despite low query volume — usually a sign of large scans.
- `pg_stat_user_tables` shows high `seq_scan` counts on large tables alongside low `idx_scan`
  counts.

## Why

Without an index the query engine must read every row in the table to find matches — a sequential
scan whose cost is O(N). With a B-tree index the engine jumps directly to matching rows — O(log N).
For a table with 10 million rows, this difference can be 4–5 orders of magnitude in I/O.

Composite index column order is critical: the engine can use an index for a prefix of its columns
but not for a non-leading column alone. A filter on `(created_at, status)` cannot use an index
defined as `(status, created_at)` when filtering only on `created_at`. Range predicates (`BETWEEN`,
`>`, `<`) must appear last in a composite index; equality columns should lead.

## Remediate

1. **Capture the slow query.** Enable `pg_stat_statements` extension (Postgres) or
   `performance_schema.events_statements_summary_by_digest` (MySQL). Identify the top queries by
   `total_time / calls` or `mean_exec_time`.

2. **Run `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)`** on the slow query with representative
   parameters. Read the plan bottom-up. Look for: `Seq Scan`, `Hash Join` on large relations, high
   `actual loops`, and `Filter` nodes removing most rows.

3. **Add an index on filter and sort columns.** Use `CREATE INDEX CONCURRENTLY` in Postgres to avoid
   locking:
   ```sql
   CREATE INDEX CONCURRENTLY idx_orders_user_created
     ON orders (user_id, created_at DESC)
     WHERE status = 'active';  -- partial index if applicable
   ```
   For MySQL use `ALTER TABLE … ADD INDEX` during low-traffic windows or pt-online-schema-change.

4. **Choose the right index type.**
   - B-tree: default; equality and range queries.
   - GIN: full-text search, array containment (`@>`), JSONB keys.
   - BRIN: time-series data on physically ordered columns (e.g., append-only event tables).
   - Partial index: when a column has high-cardinality but you only query a subset
     (`WHERE deleted_at IS NULL`).

5. **Update statistics after the index is created.** Run `ANALYZE <table>` (Postgres) so the planner
   sees the new index and up-to-date row estimates.

6. **Re-run `EXPLAIN ANALYZE`** and confirm: `Seq Scan` replaced by `Index Scan` or `Index Only
   Scan`; `actual rows` close to `rows` estimate; runtime dropped.

7. **Balance read gains against write cost.** Every index adds overhead to `INSERT`, `UPDATE`, and
   `DELETE`. Remove unused indexes: query `pg_stat_user_indexes` where `idx_scan = 0` and the index
   is older than 7 days of production traffic.

## References

- PostgreSQL documentation: `EXPLAIN`, `pg_stat_statements`, `CREATE INDEX CONCURRENTLY`
- MySQL documentation: `EXPLAIN FORMAT=JSON`, `performance_schema`
- Markus Winand — *SQL Performance Explained* (use-the-index-luke.com)
- Percona: pt-online-schema-change for online DDL on MySQL
