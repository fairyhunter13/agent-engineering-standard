---
name: error-handling-taxonomy
description: Classify errors as expected or unexpected and handle each class consistently across the codebase.
discipline: craft
tags: [error-handling, exceptions, go, rust, reliability]
---

# Error Handling Taxonomy

## When to use
Designing the error handling strategy for a new service; reviewing code for swallowed or improperly classified errors; writing an API whose callers need to distinguish recoverable from fatal failures.
Apply this any time you write code that can fail and that failure needs to be communicated to a caller or operator.

## Signal
- `catch (Exception e) { /* swallowed */ }` or `_ = riskyCall()` — errors silently discarded.
- All errors are logged at `ERROR` level, making alerts noisy and genuine problems invisible.
- API returns `500 Internal Server Error` for invalid user input that should be a `400 Bad Request`.
- Callers use string matching on error messages to determine error type rather than structured error values.
- Stack traces from internal implementation details leak into API responses visible to external clients.
- `errors.New("something went wrong")` used everywhere — no context, not wrappable, not comparable.

## Why
Inconsistent error handling is one of the most common sources of silent production failures.
When errors are swallowed, the system appears healthy while data is lost or corrupted.
When all errors are treated identically, callers cannot implement correct retry logic: retrying a `400 Bad Request` wastes resources; not retrying a `503 Service Unavailable` loses data.
When stack traces leak into external responses, they expose implementation details that aid attackers and confuse users.
The classification of an error — expected vs. unexpected — determines logging level, alert threshold, HTTP status code, and retry behavior simultaneously.

## Remediate
1. **Classify every error at its origin** into one of two classes:
   - **Expected errors** (domain errors): user input validation failure, business rule violation, not-found, unauthorized. These are normal outcomes. Log at `DEBUG` or `INFO`. Return `4xx`. Do not alert.
   - **Unexpected errors** (infrastructure/bug errors): database connection failure, nil pointer dereference, dependency timeout, assertion violation. These indicate a bug or infrastructure problem. Log at `ERROR` with full stack trace. Return `5xx`. Alert on these.
2. **Never swallow errors**: if you cannot handle an error at the current layer, wrap it with context and return it. At the top boundary (HTTP handler, CLI entry point, queue consumer), log it at the appropriate level. There is no valid reason to discard an error silently.
3. **Go: wrap errors with context and preserve the chain**: use `fmt.Errorf("loading user %d: %w", id, err)` to add context at each call site. Use `errors.Is(err, ErrNotFound)` to check for specific sentinel errors and `errors.As(err, &target)` to extract typed error values. Never wrap with `errors.New(err.Error())` — that breaks the chain.
4. **Exceptions (Java, Python, etc.)**: let exceptions propagate through business logic layers unchanged. Catch at boundaries only — HTTP handlers, queue consumers, scheduled jobs. At boundaries, classify (expected vs. unexpected), log appropriately, translate to the external representation (HTTP status, error response JSON), and do not re-throw to the caller.
5. **External-facing error messages**: return a stable, human-readable message and a machine-readable `code` string to external callers. Never include stack traces, internal service names, or database error messages in external responses. Log the full detail internally linked by a correlation ID that the caller can reference.
6. **Retriable vs. non-retriable in your API contract**: document which errors callers should retry. Standard conventions: `429 Too Many Requests` (retry with backoff), `503 Service Unavailable` (retry), `400 Bad Request` (never retry without changing the request), `401 Unauthorized` (refresh credentials first, then retry once). Implement this in your client library so callers do not have to guess.

## References
- Go blog: "Error handling and Go" (go.dev/blog/error-handling-and-go)
- Go blog: "Working with Errors in Go 1.13" — `errors.Is`, `errors.As`, `%w`
- "Release It!" — Michael T. Nygard — Chapter on stability patterns
- HTTP status codes: RFC 9110
- Rust `thiserror` and `anyhow` crates — idiomatic structured error handling
