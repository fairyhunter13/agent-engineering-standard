---
name: circuit-breaker
description: Wrap outbound calls in a circuit breaker to fast-fail when a downstream dependency is unhealthy, preventing cascading failures.
discipline: backend
tags: [resilience, distributed-systems, microservices, fault-tolerance]
---

# Circuit Breaker

## When to use

A service calls a dependency (another service, DB, external API) that can become unavailable or
slow. Caller threads or goroutines block waiting for timeouts, consuming all available capacity.
A downstream outage causes upstream P99 latency to spike as thread pools exhaust. The service needs
to degrade gracefully rather than fail completely when a dependency is unhealthy.

## Signal

- Thread pool exhaustion: all threads are blocked on `connect timeout` or `read timeout` waiting for
  a slow downstream service. New requests queue, then are rejected.
- P99 latency of the upstream service is dominated by the downstream service's timeout duration (e.g.,
  every slow request takes exactly 30 s — the timeout value).
- Cascading 5xx: one downstream service being slow causes a chain of 5xx responses up through the
  call chain.
- No fast-fail logic: the service attempts every outbound call even when the dependency has been
  returning errors for the last 5 minutes.
- Recovery after an outage is slow because the first requests after recovery are still queued behind
  timed-out requests.

## Why

Without a circuit breaker, a slow dependency blocks all threads that call it. Thread pools are
finite. When all threads are blocked waiting for a timed-out dependency, the entire service becomes
unresponsive — even for requests that don't touch the affected dependency. This is cascading failure.

The circuit breaker pattern (from Michael Nygard's *Release It!*) models a simple state machine:
- **CLOSED**: calls pass through normally. On failure, increment a counter.
- **OPEN**: failures exceed threshold. All calls fast-fail immediately without touching the
  dependency. Preserves threads and capacity.
- **HALF-OPEN**: after a probe interval, allow one test request. If it succeeds, close the circuit;
  if it fails, stay open.

Fast-failing with a fallback is better than waiting for a timeout: it frees threads immediately,
allows the dependency time to recover, and lets the service return a degraded response quickly
rather than a slow error.

## Remediate

1. **Select a circuit breaker library for your language and framework.**
   - Java/Kotlin: `resilience4j` (`CircuitBreaker` module) — the June 2026 standard; Hystrix is
     end-of-life.
   - Go: `go-breaker` (sony/gobreaker) or `resilience-go`.
   - .NET: `Polly` (`CircuitBreakerPolicy` or `AdvancedCircuitBreaker`).
   - Python: `pybreaker` or `tenacity` with `stop_after_attempt` + state tracking.

2. **Configure the state machine thresholds.**
   Typical starting values (tune to your workload):
   ```yaml
   failure_rate_threshold: 50%      # OPEN when >50% of calls fail over the window
   sliding_window_size: 10          # Count-based: 10 calls in the window
   wait_duration_open: 30s          # Stay OPEN for 30 s before probing
   permitted_calls_half_open: 3     # Allow 3 test calls in HALF-OPEN
   slow_call_rate_threshold: 80%    # Also open on slow calls (>2 s) exceeding 80%
   slow_call_duration_threshold: 2s
   ```

3. **Implement a meaningful fallback.** When the circuit is OPEN, return immediately with one of:
   - Cached data from a previous successful response.
   - A degraded but safe response (e.g., empty list, default price).
   - `503 Service Unavailable` with a `Retry-After` header.
   Do not return 500 silently — make the degradation explicit and observable.

4. **Set a timeout on the outbound call that is shorter than the breaker window.** A 30-second
   timeout with a 10-second breaker window means the breaker never opens in time. Set call timeout
   to 2–5 s; set breaker window to 10–30 s.

5. **Export circuit breaker state as metrics.** Emit: current state (CLOSED/OPEN/HALF-OPEN),
   failure count, success count, slow call count. Alert on any OPEN transition for a dependency
   that serves critical paths.

6. **Test the circuit breaker.** Use fault injection (chaos engineering) or a mock server that
   returns 503 to verify: the circuit opens at the configured threshold, fallback is returned while
   open, the circuit closes after successful probe requests.

7. **Combine circuit breaker with retry.** Apply retries inside the circuit breaker (retry does not
   count as a new circuit check); the circuit breaker is the outer layer. This way, retries handle
   transient single-request failures, while the circuit breaker handles sustained dependency failure.

## References

- Michael Nygard — *Release It!*, 2nd Edition, Chapter 5 (Stability Patterns)
- resilience4j documentation: CircuitBreaker
- Martin Fowler — CircuitBreaker pattern (martinfowler.com)
- Netflix Tech Blog: Fault tolerance in a high-volume distributed system (Hystrix origin)
