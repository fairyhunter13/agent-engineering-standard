---
name: n-plus-one-queries
description: Eliminate N+1 database query patterns by replacing per-row queries with eager loading, JOINs, or batched IN-clause fetches.
discipline: backend
tags: [database, orm, performance, sql, queries]
---

# N+1 Query Elimination

## When to use

ORM-based code issues one query per collection item — visible as a spike of near-identical queries
in slow-query logs or APM traces. Apply this skill whenever query count scales proportionally with
row count rather than remaining constant.

## Signal

- APM or ORM echo log shows dozens of identical `SELECT` statements differing only by a primary key
  or foreign key value (e.g., `WHERE user_id = 1`, `WHERE user_id = 2`, …).
- Span count in distributed traces spikes in proportion to the number of records returned by the
  outer query — a clear sign that per-row lookups are happening inside a loop.
- P99 latency climbs with data volume even though individual queries are fast; total latency is
  dominated by round-trip count, not per-query cost.
- Database slow-query log is noisy with sub-millisecond queries that appear hundreds of times per
  request.
- `pg_stat_statements` or MySQL `performance_schema` show a single query template executed thousands
  of times per minute with negligible per-execution cost.

## Why

Every ORM lazy-load fires a synchronous network round-trip to the database. For N records in a
collection, the application pays N separate round-trips — N+1 total (1 for the collection, N for
the associations). At small N this is unnoticeable; at N=100 it is painful; at N=10,000 it is
catastrophic. The root cause is the ORM transparently issuing a query each time an unloaded
association is accessed — a convenient default that is dangerous in loops.

Because each round-trip carries TCP overhead, authentication context, and query-parse cost, the
aggregate time scales linearly with N even when the DB executes each query in microseconds. No
amount of per-query optimization fixes an architectural round-trip problem.

## Remediate

1. **Enable query logging in development.** Set `echo=True` / `LOGGING` / debug query logging in
   your ORM config so every query is visible during local testing. In Rails: `config.log_level =
   :debug`. In Django: `LOGGING` with `django.db.backends`. In SQLAlchemy: `echo=True` on
   `create_engine()`.

2. **Switch to eager loading at the call site.**
   - Rails/ActiveRecord: `.includes(:association)` (emits a second `IN` query) or
     `.eager_load(:association)` (LEFT JOIN). Deeply nested: `.includes(orders: :items)`.
   - Django ORM: `select_related('fk_field')` for forward FK (JOIN), `prefetch_related('m2m')` for
     reverse/M2M (second `IN` query).
   - SQLAlchemy: `selectinload(Model.children)` or `joinedload(Model.parent)`.
   - TypeORM/Prisma: `relations: ['association']` or `include: { association: true }`.

3. **For raw SQL loops, replace with a single batched query.** Collect all IDs from the outer result
   set, then issue one `SELECT … WHERE id IN (:ids)` query. Group results by ID in application
   memory. This converts N round-trips into 1.

4. **GraphQL / DataLoader pattern.** Wrap per-entity DB calls in a `DataLoader`. DataLoader batches
   all per-request calls within a single event-loop tick into one `IN (…)` query and caches results
   for the request lifetime, eliminating both N+1 and duplicate fetches.

5. **Verify the fix.** Confirm that query count drops to ≤2 regardless of collection size. Run
   `EXPLAIN ANALYZE` on the batched query to confirm an index scan is used. Add a test that asserts
   query count using `assert_query_count(2)` helpers (Rails: `db:query_count` matchers; Django:
   `CaptureQueriesContext`).

6. **Add a regression guard.** Write a test that exercises the endpoint with a collection of ≥10
   items and asserts the total query count. Without this guard, future changes silently re-introduce
   the pattern.

## References

- Martin Fowler — *Patterns of Enterprise Application Architecture* (Lazy Load, Repository patterns)
- Django ORM: `select_related` / `prefetch_related` documentation
- DataLoader specification (github.com/graphql/dataloader)
- SQLAlchemy — Relationship Loading Techniques
