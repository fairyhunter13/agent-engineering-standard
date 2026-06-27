---
name: slos-and-error-budgets
description: Define Service Level Objectives (SLOs) as code and use error budgets to balance reliability investment against feature velocity.
discipline: infra
tags: [sre, slo, error-budget, reliability, opentelemetry]
---

# SLOs and Error Budgets

## When to use

No formal reliability targets exist for production services — "it should be reliable" is the only
stated goal. On-call response is purely reactive. Engineers and product managers debate "how
reliable is good enough" without objective data. There is no policy for when to stop shipping
features and focus on reliability.

## Signal

- The only reliability metric is "uptime percentage" — measured as binary up/down, not as a user-
  observable error rate.
- Post-incident reviews have no objective answer to "how bad was this?"
- Feature velocity is unconstrained by reliability — the team ships features during periods of high
  error rates.
- No alerting on error rate trends — pages fire only after complete outage.
- Reliability vs. velocity trade-offs are decided ad-hoc in each incident rather than by policy.
- Multiple customers report intermittent issues that don't trigger any existing alert.

## Why

SLOs make reliability commitments explicit and measurable. An error budget (the amount of
unreliability permitted within the SLO) quantifies exactly how much risk remains available to spend.
When the budget is being consumed fast, the team knows to slow feature shipping and invest in
reliability. When the budget is healthy, the team can ship confidently.

Google SRE introduced this model and it is now the June 2026 industry standard for engineering
reliability at scale. It aligns engineering effort with user impact rather than with operational
intuition.

## Remediate

1. **Define Service Level Indicators (SLIs) — the metrics that represent user experience.**
   Common SLIs:
   - **Availability**: `count(successful_requests) / count(total_requests)` over a time window.
   - **Latency**: `count(requests with latency <= 200ms) / count(total_requests)`.
   - **Error rate**: `1 - availability`.
   Good SLIs are: directly observable from user-facing telemetry, measurable continuously, and
   meaningful to the user experience.

2. **Set a Service Level Objective (SLO) — the target SLI value over a rolling window.**
   Example: "99.9% of requests succeed over a rolling 30-day window."
   This translates to: 30 days × 24 h × 60 min = 43,200 minutes × 0.1% = **43.2 minutes of error
   budget** per 30 days.
   Start conservatively: 99.5% (3.6 h budget) for new services; 99.9% for established services.

3. **Store SLO definitions as code in Git (SLOs-as-code).**
   ```yaml
   # slo.yaml
   service: payments-api
   slo:
     name: "availability"
     target: 0.999
     window: 30d
     sli:
       metric: http_requests_total
       good_filter: {status: "2xx"}
       total_filter: {}
   ```
   Tools: Sloth, pyrra, or vendor-specific (Datadog SLOs, GCP SLO monitoring).

4. **Implement multi-window burn rate alerting.**
   Alert when the error budget is being consumed faster than sustainable:
   - **Page (P1)**: 5% of the 30-day budget consumed in the last 1 hour (14.4× burn rate).
   - **Page (P2)**: 2% of the 30-day budget consumed in the last 6 hours (5× burn rate).
   - **Ticket**: 10% consumed in last 3 days (1× burn rate — on track to exhaust).
   Multi-window alerting avoids both over-alerting (short spike) and under-alerting (slow burn).

5. **Implement the error budget policy.** Write and get sign-off on this policy:
   - Budget remaining >50%: ship features freely.
   - Budget remaining 10–50%: increased caution on risky changes; review with SRE.
   - Budget exhausted (0%): freeze all feature work; focus on reliability until budget recovers.
   This policy turns error budget into an engineering decision-making tool, not just a metric.

6. **Review and revise SLOs quarterly.** SLOs should be aspirational but achievable. An SLO met 100%
   of the time for 6 months is too loose — tighten it. An SLO repeatedly missed is set too high or
   a signal of unaddressed reliability work.

7. **Share error budget status with stakeholders.** A weekly or monthly email with "30-day error
   budget: 72% remaining" gives product and leadership visibility into reliability health without
   requiring them to read dashboards.

## References

- Google SRE Book: Service Level Objectives (sre.google/sre-book)
- Google SRE Workbook: Implementing SLOs
- Sloth: SLO code generator (sloth.dev)
- pyrra: SLO framework for Prometheus
- Alerting on SLOs based on burn rate (Google SRE Workbook, Chapter 5)
