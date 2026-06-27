---
name: opentelemetry-instrumentation
description: Instrument applications with OpenTelemetry to emit traces, metrics, and logs in a vendor-neutral, consistent way.
discipline: infra
tags: [opentelemetry, observability, tracing, metrics, logging]
---

# OpenTelemetry Instrumentation

## When to use

Adding observability to a service for the first time. Migrating from a vendor-specific SDK
(Datadog tracer, AWS X-Ray SDK, custom metrics client) to vendor-neutral instrumentation. Connecting
traces to metrics to logs for a unified observability view. A new language/framework is being
onboarded and needs consistent observability with existing services.

## Signal

- No traces for an existing service — cannot attribute latency to specific operations.
- Metrics exist only in a vendor-specific format — switching APM providers requires re-instrumenting.
- Logs are not correlated to traces — `trace_id` is absent from log fields.
- Three separate observability tools (tracing, metrics, logging) with no cross-referencing.
- APM shows high-level service latency but cannot drill into individual DB queries or cache calls.
- Custom metrics use a vendor SDK directly (`statsd`, `dogstatsd`, AWS CloudWatch SDK) — locked in.

## Why

Vendor-specific observability SDKs create lock-in: switching from Datadog to Honeycomb requires
re-instrumenting every service. OpenTelemetry is the CNCF standard as of June 2026 — one API,
multiple backends. Instrument once, export anywhere.

The three pillars of observability (traces, metrics, logs) are more powerful when correlated. OTel
provides the data model and SDK to emit all three consistently, with shared context (`trace_id`,
`span_id`) linking them.

## Remediate

1. **Install the OTel SDK and auto-instrumentation package for your language and framework.**
   - **Go**: `go.opentelemetry.io/otel` + framework-specific wrappers (`otelhttp`, `otelgrpc`,
     `otelsql`).
   - **Python**: `opentelemetry-sdk` + `opentelemetry-instrumentation-django` or `-fastapi` or
     `-flask` + `opentelemetry-instrumentation-sqlalchemy`.
   - **Java**: OTel Java Agent (`opentelemetry-javaagent.jar`) — zero-code, attaches via JVM
     `-javaagent` flag. Instruments Spring Boot, JDBC, gRPC, Kafka automatically.
   - **Node.js**: `@opentelemetry/sdk-node` + `@opentelemetry/auto-instrumentations-node`.
   - **Rust**: `opentelemetry` crate + `opentelemetry-otlp`.

2. **Initialize all three providers: Tracer, Meter, Logger.**
   ```python
   from opentelemetry import trace, metrics
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.metrics import MeterProvider
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

   trace.set_tracer_provider(TracerProvider(
       resource=Resource({"service.name": "payments-api", "service.version": "1.4.2"})
   ))
   ```

3. **Configure the OTLP exporter.** Point to the OTel Collector (preferred) or directly to the
   backend:
   ```python
   exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
   ```
   Environment variable alternative (recommended for 12-factor apps):
   ```bash
   OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
   OTEL_SERVICE_NAME=payments-api
   OTEL_RESOURCE_ATTRIBUTES=service.version=1.4.2,deployment.environment=production
   ```

4. **Use the OTel API, never vendor APIs, in application code.** Application code calls
   `otel.GetTracerProvider()` — not Datadog's `tracer.StartSpan()`. The OTel SDK is the
   implementation; the API is what the application sees. This keeps application code vendor-neutral.

5. **Correlate logs with traces.** Inject `trace_id` and `span_id` from the current OTel span into
   log fields:
   ```python
   span = trace.get_current_span()
   ctx = span.get_span_context()
   logger.info("Processing payment", extra={
       "trace_id": format(ctx.trace_id, "032x"),
       "span_id": format(ctx.span_id, "016x"),
   })
   ```
   Most OTel log appenders do this automatically.

6. **Define and emit custom metrics using the OTel Metrics API.**
   ```go
   meter := otel.Meter("payments")
   paymentCounter, _ := meter.Int64Counter("payments.processed",
       metric.WithDescription("Total payments processed"))
   paymentCounter.Add(ctx, 1, attribute.String("currency", "USD"))
   ```
   Use semantic convention names where they exist (`http.server.request.duration`).

7. **Deploy the OTel Collector as a DaemonSet or sidecar.** The Collector receives OTLP from all
   applications, applies sampling, filtering, attribute redaction (PII), and then exports to one or
   more backends. This decouples application instrumentation from backend choice:
   ```yaml
   # otel-collector-config.yaml
   receivers:
     otlp:
       protocols: {grpc: {}, http: {}}
   processors:
     batch: {}
     memory_limiter:
       limit_mib: 512
   exporters:
     otlphttp/tempo: {endpoint: http://tempo:4318}
     prometheusremotewrite: {endpoint: http://prometheus:9090/api/v1/write}
   service:
     pipelines:
       traces: {receivers: [otlp], processors: [memory_limiter, batch], exporters: [otlphttp/tempo]}
       metrics: {receivers: [otlp], processors: [batch], exporters: [prometheusremotewrite]}
   ```

## References

- OpenTelemetry documentation (opentelemetry.io)
- OpenTelemetry Semantic Conventions
- OTel Collector documentation: Processors, Exporters
- CNCF Observability Whitepaper (June 2026)
