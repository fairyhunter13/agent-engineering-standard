---
name: dora-metrics
description: "Measure and improve software delivery performance using the four DORA metrics: deployment frequency, lead time, change failure rate, and MTTR."
discipline: infra
tags: [dora, devops, cicd, performance, metrics]
---

# DORA Metrics

## When to use

The team has no quantitative measure of software delivery performance. Engineering leadership wants
to justify CI/CD investment with data. Teams are comparing delivery performance across squads or
tracking improvement after a process change. The team suspects delivery performance is low but lacks
evidence to prioritize pipeline investment.

## Signal

- Deployment frequency tracked as "last Tuesday" — no automated measurement.
- Lead time (commit to production) is measured in weeks, not hours.
- No change failure rate baseline — the team does not know what percentage of deploys cause an
  incident.
- MTTR (time to restore service after an incident) is unknown.
- Delivery performance debates are based on intuition, not data.
- DORA metrics are known by name but not measured.

## Why

The DORA research program (now part of Google Cloud) has identified four metrics that are the most
reliable predictors of software delivery and organizational performance. The research covers 7+
years and tens of thousands of engineering teams. High performers on these metrics are 2x more
likely to achieve commercial goals. The metrics are the June 2026 industry standard for
quantitative DevOps assessment.

Measuring DORA metrics creates a feedback loop: the team can see the impact of process and tooling
changes on delivery performance, enabling data-driven improvement.

## Remediate

1. **Deployment Frequency — how often code reaches production.**
   - Instrument your CD pipeline (Argo CD, GitHub Actions, Spinnaker) to emit a deploy event on
     each successful production deployment.
   - Record: `deploy_timestamp`, `service`, `version`, `environment=production`.
   - Aggregate: count of production deploys per day/week.
   - Elite target: multiple deployments per day.
   - Practical start: emit a deploy event to a metrics endpoint or database from your CD pipeline's
     final production step.

2. **Lead Time for Changes — commit to production.**
   - Measure: `production_deploy_timestamp - first_commit_timestamp` for the commits in the deploy.
   - In practice: track PR creation or merge timestamp → production deploy timestamp.
   - GitHub Actions: emit an event with `github.event.pull_request.merged_at` and the deploy
     timestamp.
   - Aggregate: median and p95 lead time per week.
   - Elite target: <1 hour.

3. **Change Failure Rate — percentage of deploys causing a failure.**
   - Definition: a deploy "fails" if it triggers a rollback, a hotfix deploy within 1 hour, or a
     P1/P2 incident opened within 1 hour of the deploy.
   - Instrument: tag incidents in your incident management tool with the triggering deploy.
   - CFR = `incident-causing-deploys / total-deploys` over 30 days.
   - Elite target: <5%.
   - Practical start: manually tag incidents with the deploy that caused them; automate later.

4. **MTTR (Mean Time to Restore) — time from incident open to resolution.**
   - Measure: `incident_resolved_timestamp - incident_opened_timestamp`.
   - Source: your incident management tool (PagerDuty, Incident.io, Opsgenie) exports via API.
   - Aggregate: median MTTR per week or per severity.
   - Elite target: <1 hour.
   - Focus improvement effort: if MTTR is high, invest in runbooks, better alerting, and automated
     rollback — not just faster deployments.

5. **Build a DORA dashboard.** Store the four metric values in your metrics platform. Create a
   dashboard with weekly trends and a classification gauge:
   ```
   Elite: Deploy Daily | Lead <1h | CFR <5% | MTTR <1h
   High:  Deploy Weekly | Lead <1d | CFR <10% | MTTR <1d
   Medium: Deploy Monthly | Lead <1w | CFR <15% | MTTR <1w
   Low:   Deploy <Monthly | Lead >1m | CFR >15% | MTTR >1w
   ```

6. **Use DORA metrics to prioritize investment.** High lead time → invest in CI/CD speed and
   automation. High CFR → invest in testing, canary deployments, feature flags. High MTTR → invest
   in monitoring, runbooks, on-call tooling. Low deploy frequency → invest in reducing batch size
   and deployment friction.

7. **Share metrics with engineering leadership monthly.** DORA metrics connect engineering process
   to business outcomes. Monthly reporting with trend arrows (improving/degrading) drives
   accountability without micromanagement.

## References

- DORA: State of DevOps Report (dora.dev)
- Forsgren, Humble, Kim: *Accelerate: The Science of Lean Software and DevOps* (IT Revolution, 2018)
- Google Cloud: DORA research program
- Four Keys project (GitHub): open-source DORA metrics pipeline
