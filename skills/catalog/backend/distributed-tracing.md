---
name: distributed-tracing
description: Instrument services with distributed tracing (OpenTelemetry) to observe latency, identify bottlenecks, and correlate failures across service boundaries.
discipline: backend
tags: [observability, opentelemetry, tracing, microservices, performance]
---

# Distributed Tracing

## When to use

A multi-service architecture where a single user request touches two or more services. P99 latency
is high but the root cause cannot be attributed to a single service by looking at per-service
metrics. A request failing in one service needs to be correlated to what happened in upstream or
downstream services. Debugging a slow endpoint that involves DB queries, cache calls, and external
API calls whose individual durations are unknown.

## Signal

- High overall request latency with no obvious single-service cause — service dashboards all look
  healthy individually, but the user sees slowness.
- No cross-service request correlation — logs in Service A cannot be joined to logs in Service B for
  the same user request.
- Span fan-out visible in APM (if partially instrumented) but latency is not attributed to specific
  operations.
- Debugging a production incident requires manually correlating timestamps across multiple service
  log streams.
- No visibility into which DB query, cache call, or external API call contributes most to latency.

## Why

In a monolith, a profiler or a single log can show all operations in a request. In a distributed
system, a user request may traverse 5 services, 3 databases, and 2 external APIs — each
contributing latency. Without distributed tracing, the only visibility is per-service metrics, which
aggregate across all requests and cannot show the path of a single slow request.

Distributed tracing attaches a unique `trace_id` at the entry point and propagates it through every
service boundary. Each service records a `span` — a named, timed operation with the same `trace_id`.
The trace backend assembles all spans into a waterfall, showing exactly where time was spent across
the full request lifecycle.

OpenTelemetry is the June 2026 vendor-neutral standard; instrumentation written against the OTel
API works with any OTLP-compatible backend.

## Remediate

1. **Install the OpenTelemetry SDK and auto-instrumentation for your framework.**
   - Go: `go.opentelemetry.io/otel` + `otelhttp`, `otelsql`, `otelgrpc`
   - Python: `opentelemetry-sdk` + `opentelemetry-instrumentation-django` (or FastAPI/Flask)
   - Java: OpenTelemetry Java Agent (javaagent) — zero-code auto-instrumentation
   - Node.js: `@opentelemetry/sdk-node` + `@opentelemetry/auto-instrumentations-node`
   Auto-instrumentation captures HTTP calls, DB queries, and cache calls without manual spans.

2. **Propagate the `traceparent` header on all outbound HTTP calls.**
   Auto-instrumentation handles this if you use instrumented HTTP clients. For manual propagation:
   ```go
   // Go example
   propagator := otel.GetTextMapPropagator()
   propagator.Inject(ctx, propagation.HeaderCarrier(req.Header))
   ```
   For gRPC: use the `otelgrpc` interceptors.

3. **Create spans at service boundaries and for significant internal operations.**
   ```python
   with tracer.start_as_current_span("process_payment") as span:
       span.set_attribute("payment.amount", amount)
       span.set_attribute("payment.currency", currency)
       result = charge_card(...)
   ```
   Do not create a span for every function call — only for operations whose duration is meaningful:
   DB queries, cache calls, external APIs, and significant business operations.

4. **Add semantic attributes to spans.** Use OpenTelemetry semantic conventions:
   - HTTP: `http.method`, `http.url`, `http.status_code`
   - DB: `db.system`, `db.name`, `db.statement` (sanitize — no user values in the statement)
   - Cache: `db.system=redis`, `db.operation`
   - Error: `error.type`, `exception.message`, `exception.stacktrace`

5. **Configure the OTLP exporter.**
   Point to your OTel Collector or directly to the backend:
   ```yaml
   exporters:
     otlp:
       endpoint: "http://otel-collector:4317"
   ```
   Recommended backends (June 2026): Grafana Tempo, Honeycomb, Jaeger, Datadog APM, AWS X-Ray.

6. **Set an appropriate sampling strategy.**
   - **Head-based**: sample a fixed percentage at the trace ingress point (1–10% for high-volume).
     Simple but loses rare events.
   - **Tail-based**: buffer full traces and keep 100% of error/slow traces, sample the rest. More
     complex but higher signal. Configure via OTel Collector `tailsamplingprocessor`.

7. **Correlate traces with logs and metrics.** Inject `trace_id` and `span_id` into structured log
   fields. In your metrics platform, add `trace_id` as an exemplar on histogram observations. This
   enables jumping from a slow metric data point directly to the trace that caused it.

## References

- OpenTelemetry documentation: Tracing, Semantic Conventions
- W3C Trace Context specification
- Grafana Tempo documentation
- Google Dapper paper: "Dapper, a Large-Scale Distributed Systems Tracing Infrastructure"
