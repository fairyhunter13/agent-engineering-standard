---
name: data-partitioning
description: Partition large analytical tables so queries scan only the data they need, not the entire history.
discipline: data
tags: [data, partitioning, bigquery, parquet, performance]
---

# Data Partitioning

## When to use
Query performance degrades linearly as a time-series table grows; BigQuery or Snowflake query costs are unexpectedly high; `EXPLAIN` reveals full table scans despite date filters.
Apply this at table design time, and as a remediation when a growing table begins to cause noticeable query slowdowns or cost overruns.

## Signal
- A BigQuery query with `WHERE created_at BETWEEN '2024-01-01' AND '2024-01-07'` shows "Bytes processed: 2.4 TB" — the entire table — in the query details pane.
- `EXPLAIN` in Postgres shows `Seq Scan` on a 500 million row table despite a date predicate.
- Monthly Snowflake bill grows linearly with total data volume, not with query selectivity.
- Time-to-first-row on a dashboard query increases week over week without any change to the query itself.
- A table stores 3 years of events but every query only touches the last 30 days.

## Why
Without partitioning, the query engine cannot determine which physical storage blocks are relevant to a query — it must scan all of them.
With partitioning, the query planner prunes entire partitions that fall outside the filter range before reading a single byte of data.
For time-series event data, the access pattern is almost always "last N days" — partitioning on the time column converts a full scan into a bounded scan.
Cost in cloud data warehouses is typically proportional to bytes scanned; partitioning is the primary cost-reduction lever for large analytical workloads.

## Remediate
1. **Choose the partition column**: partition on the most common filter in your queries, almost always the event timestamp (`created_at`, `event_date`). Use date granularity (not hourly) unless your queries filter by hour and your table exceeds 1 TB.
2. **BigQuery**: `PARTITION BY DATE(created_at)`. Queries with `WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31'` prune automatically to ~31 partitions. Verify in the query details: "Bytes processed" should match only the scanned date range.
3. **PostgreSQL declarative partitioning**: `PARTITION BY RANGE (created_at)` on the parent table; child tables per month or quarter. Always add a `DEFAULT` partition to avoid errors on out-of-range inserts. Create indexes on each child partition, not the parent.
4. **Clustering / sort keys within partition**: after partitioning, add a clustering key on the next most common filter. BigQuery: `CLUSTER BY user_id, event_type`. Redshift: `SORTKEY (created_at, user_id)`. This further reduces bytes scanned within a partition.
5. **Verify pruning before declaring done**: run `EXPLAIN` (Postgres) or check the BigQuery "Bytes processed" metric before and after partitioning the table. Do not assume the optimizer will use partition pruning — confirm it does for your actual query patterns.
6. **Partition expiry for retention**: set a partition expiry policy to automatically delete old partitions. BigQuery: `partition_expiration_days = 365`. This enforces retention policy at the storage layer without a scheduled DELETE job.

## References
- BigQuery documentation: Partitioned Tables and Partition Pruning
- PostgreSQL documentation: Table Partitioning (Chapter 5)
- Snowflake documentation: Micro-Partitions and Data Clustering
- Apache Parquet: row-group statistics and predicate pushdown
- "Designing Data-Intensive Applications" — Kleppmann, Chapter 3: Storage and Retrieval
