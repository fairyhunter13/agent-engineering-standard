---
name: telemetry-cost-and-sampling
description: Control observability costs by applying intelligent sampling, retention policies, and telemetry budgets without losing signal on errors or slowness.
discipline: infra
tags: [observability, sampling, cost, opentelemetry, sre]
---

# Telemetry Cost and Sampling

## When to use

The observability bill is growing disproportionately to service traffic. Telemetry volume is growing
10x year-over-year but actionable insight is not. High-cardinality labels are bloating the metrics
store. Storage for traces or logs is running out before the intended retention window. The team
cannot determine which telemetry is actually used vs. ingested-and-forgotten.

## Signal

- Observability cost >5% of total infrastructure spend.
- Trace storage full or auto-purging before the configured retention window.
- Prometheus or metrics platform reports "too many time series" or cardinality explosions.
- Labels on metrics include user IDs, session IDs, or GUIDs — unbounded cardinality.
- 100% of traces are sampled at high request volumes (10k+ req/s) — the resulting data volume is
  terabytes/day.
- Alert fatigue from too many low-value metrics generating spurious alerts.
- The on-call engineer cannot find signal in the sea of data during an incident.

## Why

Collecting every trace, log line, and metric data point from every service sounds appealing but does
not scale. At 10,000 requests/second, 100% trace sampling generates ~10,000 trace spans/second per
service — potentially gigabytes of data per hour. The cost of storing, indexing, and querying this
data grows linearly. Meanwhile, 99% of traces are from healthy requests and provide no additional
insight over a 1% sample.

The goal is **maximum signal per dollar of telemetry cost**: capture 100% of errors, slowness, and
anomalies; sample the healthy majority at a low rate; drop high-cardinality noise.

## Remediate

1. **Apply head-based sampling at the trace ingress point.** Sample a fixed percentage of incoming
   traces — typically 1–10% depending on traffic volume. Configure in the OTel SDK or Collector:
   ```yaml
   # OTel Collector: probabilistic sampling
   processors:
     probabilistic_sampler:
       sampling_percentage: 5   # 5% of all traces
   ```
   Head-based sampling is simple and low-overhead but may miss rare error traces.

2. **Apply tail-based sampling in the OTel Collector for critical signal.** Tail-based sampling
   buffers complete traces and makes sampling decisions after the fact — always keeping error traces
   and slow traces:
   ```yaml
   processors:
     tail_sampling:
       decision_wait: 10s
       policies:
         - name: errors
           type: status_code
           status_code: {status_codes: [ERROR]}
         - name: slow-traces
           type: latency
           latency: {threshold_ms: 1000}
         - name: probabilistic-rest
           type: probabilistic
           probabilistic: {sampling_percentage: 1}
   ```
   This ensures error and slow traces are always captured while healthy-fast traces are sampled at 1%.

3. **Remove high-cardinality labels from metrics.** Every unique combination of label values creates
   a separate time series. User IDs, session IDs, request IDs, full URL paths, and GUIDs should
   never be metric labels:
   ```
   BAD:  http_requests_total{user_id="user-12345", path="/users/12345/profile"}
   GOOD: http_requests_total{endpoint="/users/:id/profile", method="GET", status="200"}
   ```
   Use recording rules to aggregate before storage if you need per-user analytics.

4. **Set retention policies aligned with query patterns.**
   - **Traces**: 7–15 days (most investigation happens within 48 h; legal holds are separate).
   - **Metrics**: 13 months (one year of data for year-over-year comparison).
   - **Logs**: 30 days hot (fast query), 90 days cold (S3/GCS, slow query), 7 years archive
     (compliance).
   Use tiered storage in Loki, Elasticsearch ILM, or Cloud Logging tiering to reduce hot-storage
   cost for aged data.

5. **Implement a telemetry budget per service.** Assign each service a monthly trace, metric, and
   log quota (e.g., 100 GB/month). Alert the service owner when usage reaches 80% of quota. This
   creates accountability and incentivizes efficient instrumentation.

6. **Use the OTel Collector's `filter` and `transform` processors to drop low-value telemetry.**
   ```yaml
   processors:
     filter/drop-health:
       traces:
         span:
           - 'attributes["http.route"] == "/healthz"'   # drop health check traces
   ```
   Health check endpoints, internal monitoring probes, and synthetic check traces rarely provide
   useful signal and can constitute 30–50% of trace volume.

7. **Audit metric usage.** Query your metrics platform for metrics with `last_used_time` > 30 days
   or with no associated alert or dashboard. Propose dropping or reducing cardinality of unused
   metrics.

## References

- OpenTelemetry Collector: tail_sampling processor documentation
- Prometheus documentation: Recording rules, cardinality
- Grafana Tempo documentation: Tail-based sampling
- AWS: Observability best practices guide
