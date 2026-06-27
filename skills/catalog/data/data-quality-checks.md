---
name: data-quality-checks
description: Gate pipeline loads with automated quality assertions to prevent bad data from reaching consumers.
discipline: data
tags: [data, quality, dbt, great-expectations, validation]
---

# Data Quality Checks

## When to use
Data enters a warehouse or lake from multiple sources with differing reliability; dashboards feed executive decisions; a data contract exists with downstream consumers.
Apply this before any new table or pipeline goes into production, and retroactively when anomalies are discovered in existing reports.

## Signal
- A dashboard shows an unexpected 30% drop in revenue with no corresponding business event.
- Null values appear in columns that should always be populated (order totals, user IDs).
- Row count in a daily load is zero because the upstream source sent an empty file — and no alert fired.
- A metric looks different across two reports querying "the same" data because one joined on a broken FK.
- Engineers discover data issues only when a stakeholder reports something "looks wrong."
- No automated checks run between data arriving and reports refreshing.

## Why
Bad data silently corrupts business decisions.
Data quality issues discovered in a report require a reverse trace through potentially many pipeline stages, each of which may have already propagated the error downstream.
The cost of catching a bad load before it reaches the warehouse is an order of magnitude lower than correcting it after stakeholders have made decisions based on it.
Automated quality gates create a formal contract between the pipeline and its consumers: if the checks pass, the data meets the agreed specification.

## Remediate
1. **Define quality rules explicitly** before writing pipeline code: not-null constraints on key columns; value in expected enumerated set; referential integrity (every `order.user_id` exists in `users`); row count within ±20% of the previous day's load; no duplicate natural keys.
2. **Implement with dbt tests** (for warehouse-native checks): `schema.yml` with `not_null`, `unique`, `accepted_values`, `relationships` tests. Add custom SQL tests for business rules: `assert_revenue_positive`, `assert_no_future_dates`.
3. **Implement with Great Expectations** (for pipeline-level checks outside dbt): define expectation suites per dataset; run as a checkpoint step before the load commits. GE integrates with Airflow, Prefect, and dbt.
4. **Block the pipeline on breach**: quality checks must run before the downstream load step. If a check fails, the load does not proceed, an alert fires, and the previous known-good data remains in place. Never load and check in parallel.
5. **Alert with context**: send alerts with the specific rule that failed, the observed value, the expected threshold, and a direct link to the failing data sample. A bare "data quality check failed" alert is not actionable.
6. **Data contract**: agree on schema + quality SLAs (null rate, row count, freshness SLA) with downstream consumers before go-live. Document them in the table's `schema.yml` description. Treat a quality regression as a contract breach requiring a postmortem.

## References
- dbt documentation: Testing (`schema.yml` tests, `dbt test`)
- Great Expectations documentation: Expectation Suites and Checkpoints
- Data Contract Specification (datacontract.com)
- Monte Carlo / Bigeye / Anomalo: data observability platforms (reference architecture)
- "The Data Quality Imperative" — O'Reilly
