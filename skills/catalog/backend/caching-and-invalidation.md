---
name: caching-and-invalidation
description: Add read-through/write-through caching to reduce DB load, and design a correct invalidation strategy to avoid stale data.
discipline: backend
tags: [caching, redis, performance, database, invalidation]
---

# Caching and Invalidation

## When to use

Database read latency dominates endpoint response time. Repeated identical queries consume DB CPU
without new information. Hot-path computation (aggregation, rendering, complex joins) is expensive
and its result changes infrequently. Traffic spikes cause DB saturation on reads.

## Signal

- DB CPU is dominated by read queries despite relatively low write volume.
- APM shows the same DB query appearing hundreds of times per minute with identical results.
- Cache hit rate is <50% for data that should be cacheable.
- Response time spikes on popular items — the "thundering herd" after a cache miss.
- No explicit cache invalidation logic — all cached data expires by TTL only.
- Stale data reported by users: page shows old value minutes after an update.

## Why

The fundamental cache trade-off: hit rate vs. correctness. TTL-only invalidation is a blunt
instrument — a short TTL minimizes staleness but defeats caching; a long TTL may serve stale data.
The correct model is event-driven invalidation: when data changes, invalidate or update the cache
immediately, making TTL a safety net rather than the primary freshness mechanism.

A second danger is cache stampede: when a popular cache key expires, many concurrent requests all
miss and simultaneously hit the DB, potentially overwhelming it. This must be handled explicitly.

Phil Karlton's observation — "There are only two hard problems in computer science: cache
invalidation and naming things" — reflects real engineering pain. The invalidation strategy must be
designed alongside the caching strategy, not added later.

## Remediate

1. **Identify candidates.** Cache data that is: (a) read far more than it is written, (b) expensive
   to compute, (c) tolerates bounded staleness. User profile, product catalog, configuration, and
   computed aggregates are typical candidates. Per-session data is usually not.

2. **Choose a caching strategy.**
   - **Cache-aside (lazy loading)**: on cache miss, load from DB and populate cache. Application
     reads cache first; only fetches from DB on miss. Simplest to implement; risk of stale data
     between write and TTL expiry.
   - **Write-through**: on every write, update cache and DB synchronously. Cache is always warm;
     adds write latency; requires cache to be available for writes to succeed.
   - **Write-behind (write-back)**: write to cache immediately; async flush to DB. High performance;
     risk of data loss if cache crashes before flush.

3. **On mutation, explicitly invalidate or update the cache key.** Do not rely on TTL alone for
   correctness-sensitive data:
   ```python
   def update_user(user_id, data):
       db.update(user_id, data)
       cache.delete(f"user:{user_id}")   # invalidate
       # or: cache.set(f"user:{user_id}", data, ex=3600)  # update
   ```

4. **Prevent cache stampede with one of these techniques:**
   - **Mutex/lock on miss**: only one request fetches from DB; others wait for the result.
   - **Probabilistic early expiry** (XFetch): randomly refresh keys slightly before TTL expiry to
     spread the load.
   - **Stale-while-revalidate**: serve the stale value immediately while refreshing in background.

5. **Never use a shared cache key for user-specific data.** Ensure cache keys include the user ID or
   tenant ID for any data that differs per user: `user:{user_id}:profile`, not `profile`.

6. **Set TTL appropriate to staleness tolerance.** Configuration data: hours. Product catalog: 5–30
   min. Session data: user session length. Never set unlimited TTL unless you have perfect
   invalidation.

7. **Monitor cache health.** Track: hit rate, miss rate, eviction rate, memory usage. Alert on hit
   rate dropping below threshold (e.g., <70% for a hot path) — it may indicate a key pattern change
   or cache misconfiguration.

8. **Use Redis 7+ with keyspace notifications** to build reactive invalidation: on DB write, publish
   an invalidation event; a subscriber deletes or updates the cache key. This decouples cache
   invalidation from the write path.

## References

- Martin Fowler — Cache-Aside pattern (martinfowler.com)
- AWS ElastiCache documentation: Caching strategies
- Redis documentation: Key expiration, Lua scripting
- XFetch algorithm: "Optimal Probabilistic Cache Stampede Prevention" (Vattani et al.)
