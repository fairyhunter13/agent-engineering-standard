---
name: retries-with-backoff-and-jitter
description: Implement retry logic with exponential backoff and random jitter to handle transient failures without amplifying load.
discipline: backend
tags: [reliability, resilience, distributed-systems, http, retries]
---

# Retries with Exponential Backoff and Jitter

## When to use

Calling external APIs or downstream services that can fail transiently (network blips, 429, 503).
Handling network errors, timeouts, or connection resets that are expected to resolve on their own
within seconds. Any client-side code that calls a dependency that is not perfectly reliable.

## Signal

- Retry storms visible in APM: a wave of retries arrives synchronously seconds after an initial
  failure, spike-loading the recovering dependency.
- All retries use a fixed interval (e.g., sleep 1 second) — clients synchronize and hit the
  recovering service in lockstep.
- Retry amplification: N clients × M retries = N*M requests arriving simultaneously.
- No retry logic at all — transient failures propagate to the user as errors that would have
  resolved in 500 ms.
- Missing circuit breaker: retries continue indefinitely even when the dependency is down for
  minutes.

## Why

Fixed-interval retries from many clients synchronize. If 1,000 clients all retry exactly 1 second
after a 503, they send 1,000 simultaneous requests to a recovering service — potentially
overwhelming it again and causing a "thundering herd". Exponential backoff increases wait time
between retries, reducing retry pressure. Jitter adds random noise to desynchronize retries across
clients, spreading load over time rather than concentrating it.

Retrying on the wrong status codes causes harm: retrying a 400 Bad Request is pointless (the
request is malformed and will fail again); retrying a 401 Unauthorized can cause account lockout.

## Remediate

1. **Define retry-safe status codes.** Retry on transient errors only:
   - **Yes**: 429 (rate limited), 503 (service unavailable), 504 (gateway timeout), 502 (bad
     gateway), `ECONNRESET`, `ETIMEDOUT`, `ECONNREFUSED`.
   - **Never**: 400 (bad request — client bug), 401 (unauthorized — credentials issue), 403
     (forbidden), 404 (not found), 405 (method not allowed), 409 (conflict), 422 (unprocessable).

2. **Use exponential backoff with jitter.** The canonical formula:
   ```
   sleep = min(cap, base * 2^attempt) + random_uniform(0, jitter)
   ```
   Typical values: `base = 0.5s`, `cap = 30s`, `jitter = 1s`. This gives:
   - Attempt 1: ~0.5–1.5 s
   - Attempt 2: ~1–3 s
   - Attempt 3: ~2–6 s
   - Attempt 4: 30 s (capped)

3. **Respect `Retry-After` headers.** If the response includes a `Retry-After: 60` header, use that
   value as the minimum wait time instead of the calculated backoff.

4. **Set a maximum retry count and a total timeout budget.**
   - Max retries: 3–5 is typical.
   - Total budget: the sum of all waits plus expected request durations must not exceed the caller's
     own SLA. If your endpoint must respond in 5 s, don't configure 3 retries with 2 s waits each.

5. **Use a tested retry library.**
   - Python: `tenacity` — `@retry(wait=wait_exponential(multiplier=0.5, max=30), stop=stop_after_attempt(4))`
   - Java: `resilience4j-retry` with exponential backoff config
   - Go: `go-retry` or manual retry loop with `time.Sleep`
   - Node.js: `p-retry` or `axios-retry`

6. **Log every retry attempt.** Include: attempt number, delay, error code/message, upstream URL.
   This is essential for diagnosing retry storms in production.

7. **Combine with a circuit breaker** (see `backend/circuit-breaker`). Retries handle transient
   failures lasting milliseconds to seconds; circuit breakers handle sustained outages lasting
   minutes. Retrying into an open circuit wastes time and load — the circuit breaker should reject
   immediately.

8. **Do not retry on POST requests unless idempotency keys are in use.** A POST that modifies state
   may have partially succeeded. Retrying without an idempotency key causes duplicates.

## References

- AWS Architecture Blog: "Exponential Backoff and Jitter" (aws.amazon.com/blogs/architecture)
- resilience4j documentation: Retry
- tenacity Python library documentation
- Google Cloud documentation: Retry strategy best practices
