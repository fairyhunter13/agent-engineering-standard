---
name: pipeline-idempotency
description: Design ETL/ELT stages to be safely re-runnable without corrupting or duplicating data.
discipline: data
tags: [data, pipelines, idempotency, etl, reliability]
---

# Pipeline Idempotency

## When to use
Building ETL/ELT pipelines that may be re-run on failure or scheduled multiple times.
Apply this whenever a pipeline writes to a database, object store, or data warehouse and could be interrupted mid-run.

## Signal
- Re-running a failed pipeline creates duplicate records in the target table.
- A partial pipeline run leaves the database in an inconsistent or half-loaded state.
- No deduplication logic on the load step — inserts are unconditional `INSERT INTO`.
- Incident post-mortem shows "we couldn't retry the job safely, so we had to restore from backup."
- Primary keys are auto-increment integers generated at load time rather than derived from source data.
- Manual intervention is required after every pipeline failure.

## Why
Pipelines fail — network timeouts, upstream schema changes, quota exhaustion, transient cloud errors.
The only safe operational posture is that any pipeline stage can be re-run without operator intervention.
A non-idempotent pipeline forces a choice between data loss (skip the retry) and data corruption (run it again).
Distributed systems guarantee at-least-once delivery, so idempotency is not optional — it is the contract that makes retry safe.
The cost of a corrupted data load is always higher than the cost of designing it correctly upfront.

## Remediate
1. **Insert semantics**: Replace bare `INSERT INTO` with `INSERT … ON CONFLICT (natural_key) DO NOTHING` (Postgres) or `MERGE` / `UPSERT` (BigQuery, Snowflake, Redshift). Never use unconditional bulk insert on a table with a uniqueness constraint.
2. **Deterministic IDs**: Derive record IDs from source data using a stable hash: `MD5(source_system || source_id || partition_date)`. Auto-increment PKs are non-idempotent because each retry generates a new ID for the same logical record, creating silent duplicates.
3. **Batch state tracking**: Maintain a `pipeline_runs` table recording `(pipeline_name, batch_id, status, processed_at)`. On entry, check whether this batch has already completed successfully and skip if so. Mark status `IN_PROGRESS` before starting; `DONE` only after commit.
4. **Staging table pattern**: Load into a staging table first (`stg_orders`), then atomically swap with a `TRUNCATE + INSERT` inside a transaction, or use `CREATE TABLE … AS SELECT` + rename. If the load fails, the target table is untouched and the operation is safe to retry.
5. **Watermark checkpointing**: Record the last successfully processed watermark (timestamp or offset) in a persistent store. On retry, resume from the checkpoint, not from the beginning. For Kafka/Kinesis: commit offsets only after successful downstream write, not on receipt.
6. **Partition-level atomicity**: For partitioned tables (BigQuery, Hive, Iceberg), write each partition as an independent atomic operation. A failed run for `2024-01-15` only needs to retry that partition, not the entire history. Use `OVERWRITE PARTITION` semantics where available.

## References
- Exactly-once and at-least-once delivery semantics (distributed systems theory)
- The Data Warehouse ETL Toolkit — Kimball & Caserta
- Apache Spark: idempotent sinks and checkpoint directories (`spark.sql.streaming.checkpointLocation`)
- Kafka 0.11+ transactional producer API for exactly-once semantics
- Apache Iceberg: atomic partition replacement
