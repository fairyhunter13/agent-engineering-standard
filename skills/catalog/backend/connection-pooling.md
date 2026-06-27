---
name: connection-pooling
description: Configure database connection pools to prevent connection exhaustion, reduce connection overhead, and tune pool size to workload.
discipline: backend
tags: [database, performance, postgresql, mysql, pool]
---

# Database Connection Pooling

## When to use

Services report "too many connections" DB errors under load. Connection acquisition time appears in
APM as a dominant latency contributor. The DB's `max_connections` limit is approached or breached.
A new microservice is being deployed alongside existing services sharing the same DB instance.

## Signal

- PostgreSQL error: `FATAL: remaining connection slots are reserved for non-replication superuser
  connections` or `FATAL: sorry, too many clients already`.
- MySQL error: `ERROR 1040 (08004): Too many connections`.
- APM shows a "pool wait" span that grows disproportionately under load — requests waiting for an
  available connection rather than executing queries.
- `pg_stat_activity` shows hundreds of idle connections from application hosts.
- Pool `waitQueueSize` or `pendingAcquires` metric trending upward.
- Service latency spikes when pod count scales up — each new pod opens its own pool, exhausting DB
  connections.

## Why

Opening a database connection is expensive: it involves TCP handshake, TLS negotiation, PostgreSQL
authentication, and backend process allocation (in Postgres, each connection spawns a backend
process consuming ~5–10 MB). For services handling thousands of requests per second, opening a new
connection per request is prohibitive.

Without pooling, each application thread holds a connection for the duration of request processing,
including time spent in application logic, serialization, and network I/O to the client — not just
DB query time. This wastes connections. Connection poolers keep a smaller pool of live connections
and lend them to requests only while a query is executing (transaction-mode pooling).

## Remediate

1. **Set pool size with the hardware-appropriate formula.**
   The HikariCP/PgBouncer rule of thumb: `pool_size = (effective_cpu_cores * 2) + effective_spindle_count`.
   For a DB server with 8 CPU cores and SSD storage (1 spindle): `pool_size = 8 * 2 + 1 = 17`.
   Total connections across all application instances must not exceed `max_connections - 5` (reserve
   for admin/replication).

2. **Configure min-idle connections.** Set `minimumIdle` (HikariCP) or `min_pool_size` to a value
   that avoids cold-start latency during traffic bursts. A reasonable default is half of `poolSize`.

3. **Enable connection validation.** Set `connectionTestQuery` (JDBC) or `testOnBorrow` (c3p0) to
   run a lightweight `SELECT 1` before lending a connection. This detects dead connections before
   they reach the application. HikariCP validates connections in the background without a test query.

4. **Deploy PgBouncer for Postgres in high-concurrency environments.** PgBouncer in **transaction
   mode** multiplexes many application connections over a small number of server connections. A
   service with 50 app threads can share 5–10 server connections through PgBouncer. Note: transaction
   mode does not support prepared statements or advisory locks — test compatibility.

5. **Separate pool configurations by query type.** Long-running report queries and short OLTP
   queries should use separate pools with different timeout settings. A slow report should not
   exhaust the pool used by real-time API traffic.

6. **Set connection timeouts.** Configure `connectionTimeout` (max wait for a connection from the
   pool), `idleTimeout` (return idle connections to the server), and `maxLifetime` (recycle
   connections proactively to avoid stale connections). HikariCP defaults are sensible starting
   points.

7. **Monitor pool metrics.** Export: `pool.totalConnections`, `pool.activeConnections`,
   `pool.idleConnections`, `pool.waitTime` (time waiting for a connection). Alert when
   `pool.waitTime` p99 > 50 ms or `pool.activeConnections / pool.totalConnections > 0.9`.

8. **Account for horizontal scaling.** When using Kubernetes HPA, each new pod opens its own pool.
   At 10 pods × pool_size=20 = 200 total connections. Ensure `max_connections` is set above this
   total, or use PgBouncer as a central pool shared across all pods.

## References

- HikariCP documentation: Pool sizing
- PgBouncer documentation: Transaction pooling mode
- PostgreSQL documentation: `pg_stat_activity`, `max_connections`
- Brandon Liu: "The Absolute Minimum Every Programmer Must Know About DB Connection Pooling"
