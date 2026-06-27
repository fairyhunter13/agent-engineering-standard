---
name: backfill-safety
description: Run historical data backfills without locking production tables or corrupting current data.
discipline: data
tags: [data, backfill, batch, idempotency, etl]
---

# Backfill Safety

## When to use
Running a historical backfill across large datasets; re-processing events after a bug fix; populating a new derived column from existing source data; replaying a Kafka topic into a new sink.
Apply this any time you need to process historical data in a system that is also serving live production traffic.

## Signal
- The backfill job acquires a table-level lock and blocks production reads/writes for minutes.
- The backfill overwrites correct recent data because it unconditionally updates rows.
- A 48-hour backfill fails at hour 40 with no checkpoint, forcing a restart from scratch.
- No progress tracking — the only way to know if it is running is to check row counts manually.
- The backfill consumes 100% of database CPU, degrading the production application.
- After the backfill, a subset of rows have the wrong value because the job processed ranges out of order.

## Why
Uncontrolled backfills are a production incident waiting to happen.
A long-running, resource-intensive, non-idempotent job on a live production database combines three separate failure modes.
Lock contention degrades user-facing latency; unthrottled I/O starves the primary workload; a non-resumable job wastes all progress on failure.
The key insight is that a backfill is a batch migration — it should be designed with the same rigor as a database migration: small, safe, reversible steps.

## Remediate
1. **Batch in small chunks**: process 1,000–10,000 rows per batch, using a cursor or watermark (last processed `id` or `created_at`). The batch size should be chosen so each batch completes in under 1 second and holds row-level locks for no more than 100ms.
2. **Idempotent updates only**: use `UPDATE … SET new_col = derive(source_col) WHERE new_col IS NULL` rather than unconditional updates. This means re-running the backfill skips already-processed rows and is safe to restart at any point.
3. **Rate limit between batches**: sleep 50–500ms between batches to cap the I/O rate. Expose the sleep duration and batch size as configurable parameters. Monitor DB CPU during the backfill and tune the sleep upward if it is impacting production.
4. **Checkpoint progress**: record the last successfully processed watermark in a durable store (a dedicated `backfill_state` table or a Redis key). On restart, read the checkpoint and resume from there. Log progress every N batches: rows processed, rows remaining, estimated completion time.
5. **Test on a 1% sample first**: run the backfill logic on a representative sample; validate correctness of the output before committing to the full run. For irreversible operations (deletes, anonymization), test on a staging replica with production-scale data.
6. **Large-table strategies**: for tables with hundreds of millions of rows, prefer a shadow-table approach: write new data to `orders_new`, swap table names, backfill the delta. For Postgres: consider `pg_partman` partition detach-reattach. For BigQuery/Snowflake: use partition overwrite, not row-level update.

## References
- "Safe Database Migrations" — Will Larson
- Stripe Engineering Blog: "Online Migrations at Scale"
- GitHub Engineering Blog: "Reducing Friction in Data Migrations"
- PostgreSQL documentation: `pg_partman` and partition management
- Apache Kafka: consumer replay via offset reset to earliest
