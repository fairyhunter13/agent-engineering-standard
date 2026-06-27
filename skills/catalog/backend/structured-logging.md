---
name: structured-logging
description: Emit machine-parseable structured logs (JSON) with consistent fields so logs are searchable, alertable, and correlated across services.
discipline: backend
tags: [observability, logging, json, monitoring, opentelemetry]
---

# Structured Logging

## When to use

Logs are plaintext and difficult to query in aggregation tools. Log aggregation platforms (Loki,
Elasticsearch, Cloud Logging, Splunk) cannot reliably parse log fields because format varies by
code path. No correlation between log lines from different services for a single user request.
Teams spend time `grep`-ing rather than querying.

## Signal

- Log format is `printf`-style or varies between code paths: `"User 123 logged in"` vs `"Login for
  user=456"` — field names are inconsistent and position-dependent.
- No `trace_id` or `request_id` field in logs — correlating a slow request across service logs
  requires manual timestamp scanning.
- Log aggregation tool shows all log entries as raw text with no parsed fields.
- Alerting on log content requires complex regex patterns rather than field equality.
- Secrets or PII appear in log output due to unstructured string interpolation.
- Severity is conveyed by text prefix (`[INFO]`, `[ERROR]`) rather than a machine-readable field.

## Why

Plaintext logs are for humans; structured logs are for both humans and machines. When logs have
consistent, named fields, they become queryable (`level="error" AND service="payments"`), alertable
(trigger on `http.status >= 500`), and correlatable (join on `trace_id`). A log aggregation
platform can index named fields for fast search; it cannot reliably parse ad-hoc text formats.

Structured logging is the foundation of the three pillars of observability (logs, metrics, traces)
and enables correlation across them. OpenTelemetry's log data model formalizes this as the June
2026 standard.

## Remediate

1. **Replace ad-hoc string interpolation with a structured logger.**
   - Go: `zerolog` (zero-allocation) or `slog` (standard library as of Go 1.21).
   - Python: `structlog` (integrates with `logging`).
   - Node.js: `pino` (fastest) or `winston` (most configurable).
   - Java: `logback` with `logstash-logback-encoder` for JSON output.
   - Rust: `tracing` with `tracing-subscriber` JSON formatter.

2. **Define a mandatory base field set.** Every log line must include:
   ```json
   {
     "timestamp": "2026-06-27T10:30:00.000Z",
     "level": "info",
     "service": "payments-api",
     "version": "1.4.2",
     "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
     "span_id": "00f067aa0ba902b7",
     "request_id": "req_01J4KX2Y...",
     "message": "Payment processed"
   }
   ```
   Additional context fields are additive: `user_id`, `order_id`, `http.method`, `http.status`,
   `duration_ms`.

3. **Use log levels correctly.**
   - `ERROR`: an actionable failure that requires investigation; should trigger an alert.
   - `WARN`: unexpected but handled; may indicate a trend worth monitoring.
   - `INFO`: normal lifecycle events — service started, request completed, job finished.
   - `DEBUG`: fine-grained diagnostic data for development; should be disabled in production by
     default or sampled.
   Never log at `ERROR` for expected business conditions (e.g., "user not found" is `INFO`).

4. **Propagate `trace_id` and `span_id` from the incoming request through all log lines.**
   Extract from the W3C `traceparent` header on ingress:
   ```
   traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
   ```
   Use middleware to set the IDs into the request context; configure the logger to read from context.
   This is automatic when using OpenTelemetry SDK auto-instrumentation.

5. **Never log PII or secrets.** Do not log: passwords, auth tokens, credit card numbers, SSNs, full
   email addresses (in contexts where they are sensitive), or private keys. Use a log scrubbing
   middleware or OTel Collector `redaction` processor as a safety net, but prevention at the call
   site is mandatory.

6. **Emit logs to stdout/stderr only.** Let the container runtime or node agent collect and forward
   logs. Do not write to local files in a container — they are lost on restart and complicate
   aggregation.

7. **Configure the OTel Collector log pipeline** if using OpenTelemetry: receive logs via OTLP or
   file; apply parsing, field normalization, and redaction; export to your backend (Loki, Splunk,
   Cloud Logging). This centralizes log processing without touching application code.

## References

- OpenTelemetry Log Data Model specification
- Pino documentation: JSON logging for Node.js
- structlog documentation (Python)
- W3C Trace Context specification (traceparent header)
- Twelve-Factor App: Logs (12factor.net/logs)
