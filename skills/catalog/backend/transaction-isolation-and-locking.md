---
name: transaction-isolation-and-locking
description: Choose the correct isolation level and locking strategy to prevent anomalies (dirty reads, lost updates, phantom reads) without causing deadlocks.
discipline: backend
tags: [database, transactions, concurrency, isolation, locking]
---

# Transaction Isolation and Locking

## When to use

Race conditions, lost updates, or deadlocks appear under concurrent load. Monetary or inventory
calculations produce inconsistent results. Tests pass in isolation but fail under concurrent access.
Any time two concurrent transactions access overlapping rows, isolation and locking deserve explicit
thought.

## Signal

- Deadlock errors in application logs (`ERROR: deadlock detected` in Postgres; `Deadlock found when
  trying to get lock` in MySQL).
- Inconsistent aggregate results — account balances don't add up; inventory goes negative despite
  check-before-update logic.
- `SELECT … FOR UPDATE` queries piling up in `pg_stat_activity` with `wait_event_type = Lock`.
- Duplicate key violations under concurrent insert of logically unique records.
- Lost-update bugs: two concurrent processes each read value 10, both add 1, both write 11 instead
  of the correct 12.
- Unit tests that pass sequentially but flake under parallel test execution.

## Why

SQL's default isolation level — **Read Committed** — allows non-repeatable reads and lost updates.
Two transactions can both read the same row, compute a new value, and write it back; the second
write silently overwrites the first. This is the lost-update anomaly.

Higher isolation levels prevent anomalies but increase contention: **Repeatable Read** prevents
non-repeatable reads; **Serializable** prevents phantom reads and write skew, but forces serial
ordering of conflicting transactions. The cost of getting isolation wrong ranges from incorrect data
to application deadlock.

## Remediate

1. **Identify the anomaly type before choosing a fix.**
   - Dirty read: reading uncommitted data from another transaction. Prevented by Read Committed (the
     Postgres default).
   - Lost update: two transactions read-modify-write the same row; one overwrites the other.
   - Non-repeatable read: the same row read twice in a transaction returns different values.
   - Phantom read: a range query re-executed returns different rows.
   - Write skew: two transactions each check a condition and make a decision based on data the other
     is about to change.

2. **For lost updates: use pessimistic or optimistic locking.**
   - Pessimistic: `SELECT … FOR UPDATE` locks the row for the transaction duration. Safe but blocks
     other readers under high concurrency.
   - Optimistic: add a `version INTEGER` column. Read version; write only if `WHERE id = :id AND
     version = :read_version`; increment version. Retry on 0-rows-affected. Best for low-contention
     workloads.

3. **For phantom reads and write skew: use `SERIALIZABLE`.**
   Postgres's SSI (Serializable Snapshot Isolation) detects serialization anomalies without locking.
   Set `isolation_level = SERIALIZABLE` for the transaction; handle `ERROR: could not serialize
   access` (SQLSTATE 40001) with application-level retry.

4. **Minimize transaction scope — lock late, release early.**
   Keep transactions as short as possible. Never call external services, send emails, or perform slow
   computations inside a database transaction. Long transactions hold locks and block other
   transactions.

5. **Prevent deadlocks by acquiring locks in a consistent global order.**
   Deadlocks occur when transaction A locks row 1 then row 2, while transaction B locks row 2 then
   row 1. Fix: always lock rows in the same deterministic order (e.g., sorted by primary key).
   Use `ORDER BY id FOR UPDATE` when locking multiple rows.

6. **Handle deadlock errors with retry logic.** Applications must catch deadlock exceptions and retry
   the entire transaction. Deadlocks are a normal occurrence under concurrency — not a bug — but they
   must be retried at the application layer.

7. **Monitor lock waits.** Use `pg_locks` joined with `pg_stat_activity` to observe blocked
   transactions in real time. Alert when average lock wait time exceeds 100 ms.

## References

- PostgreSQL documentation: Transaction Isolation, Explicit Locking
- Martin Kleppmann — *Designing Data-Intensive Applications*, Chapter 7 (Transactions)
- Postgres SSI paper: "Serializable Snapshot Isolation in PostgreSQL" (Ports & Gritter, 2012)
- MySQL InnoDB locking documentation
