---
name: rate-limiting-and-backpressure
description: Protect services from overload by enforcing per-client rate limits and applying backpressure through controlled request shedding.
discipline: backend
tags: [reliability, api, throttling, backpressure, distributed-systems]
---

# Rate Limiting and Backpressure

## When to use

A single client can exhaust capacity for all other clients. Traffic spikes overwhelm downstream
services. A scraper or misconfigured client sends unbounded requests. The service needs to enforce
fair-use guarantees in a multi-tenant environment. A downstream dependency is slower than the
upstream call rate.

## Signal

- Latency spikes visible in APM during burst traffic from a single API key or IP.
- Database connection pool exhausted — all connections in use, new requests queuing.
- Memory or CPU saturation triggered by a single consumer.
- Thread pool or goroutine count growing unboundedly under sustained traffic.
- No `Retry-After` header in 429 responses; clients retry immediately and amplify the problem.
- Queue depth growing without bound — the service cannot drain it as fast as it fills.

## Why

Without rate limiting, a noisy neighbor, a misconfigured client, or a deliberate DDoS exhausts
shared resources — CPU, DB connections, memory — and degrades service for all callers. The
infrastructure is a shared resource; individual consumers must be constrained to their fair share.

Backpressure is the complementary mechanism: instead of accepting work indefinitely and queuing it
until memory is exhausted, a system under load actively signals overload and rejects excess work
early. Early rejection with a clear error is better than silent degradation or OOM crash. Carl
Hewitt's actor model and reactive systems manifesto both identify backpressure as fundamental to
resilience.

## Remediate

1. **Choose an algorithm.** Token bucket and sliding window counter are the most common:
   - **Token bucket**: each API key has a bucket of N tokens refilled at rate R/s. Each request
     consumes 1 token. When empty, requests are rejected. Allows burst up to bucket size.
   - **Sliding window counter**: count requests in a rolling time window (e.g., 100 req/min). No
     burst allowance. More predictable.
   - **Fixed window counter**: simplest; susceptible to boundary bursts.

2. **Apply rate limiting at the API gateway, not only in application code.** Kong (`rate-limiting`
   plugin), Envoy (`local_rate_limit` / `global_rate_limit`), NGINX (`limit_req_zone`), and AWS API
   Gateway all support rate limiting natively. Gateway-level enforcement stops traffic before it
   reaches application servers.

3. **Return `429 Too Many Requests` with a `Retry-After` header:**
   ```http
   HTTP/1.1 429 Too Many Requests
   Retry-After: 60
   X-RateLimit-Limit: 1000
   X-RateLimit-Remaining: 0
   X-RateLimit-Reset: 1719864000
   ```
   Include headers that tell the client its current quota and reset time so it can self-throttle.

4. **Rate limit per caller identity, not just IP.** IP-based limiting is bypassed by distributed
   clients. Use: API key, JWT subject claim, or authenticated user ID. Apply stricter limits to
   unauthenticated callers.

5. **Apply per-route limits, not just global.** An expensive endpoint (bulk export, report
   generation) deserves tighter limits than a cheap read endpoint. Set limits per route or resource
   type in addition to per-key totals.

6. **Implement backpressure via queue depth limits.** When a work queue depth exceeds a threshold,
   reject new enqueue requests with `503 Service Unavailable` and `Retry-After`. Do not accept work
   you cannot drain — a growing queue delays all work equally and eventually causes OOM.

7. **Use Redis for distributed rate limiting.** A single Redis counter (INCR + EXPIRE or Lua script)
   is shared across multiple application instances. Use Lua for atomic check-and-increment:
   ```lua
   local count = redis.call('INCR', KEYS[1])
   if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
   return count
   ```

8. **Test rate limiting in CI.** Write an integration test that sends N+1 requests and asserts the
   (N+1)th returns 429. Verify `Retry-After` is present.

## References

- IETF RFC 6585: Additional HTTP Status Codes (429)
- Envoy documentation: Rate Limiting
- Kong documentation: Rate Limiting Plugin
- Martin Kleppmann — *Designing Data-Intensive Applications*, Chapter 12
- The Reactive Manifesto (reactivemanifesto.org)
