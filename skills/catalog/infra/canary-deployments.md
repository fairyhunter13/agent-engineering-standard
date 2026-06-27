---
name: canary-deployments
description: Roll out changes to a small percentage of traffic first, measure error rate and latency, and auto-rollback if SLO is breached.
discipline: infra
tags: [deployment, kubernetes, canary, progressive-delivery, argo-rollouts]
---

# Canary Deployments

## When to use

Changes are risky or difficult to fully validate in staging — because staging does not replicate
production data patterns, traffic volume, or third-party integration behavior. The team needs
real-user traffic validation before committing to a full rollout. The blast radius of a bad deploy
must be limited to a small fraction of users. Feature flags alone are insufficient because the risk
is in the infrastructure or runtime behavior, not the feature logic.

## Signal

- Post-deploy incidents are discovered only after 100% of traffic is on the new version — by which
  point all users are affected.
- Staging environment is not a reliable predictor of production behavior (different data scale,
  different traffic patterns, missing integrations).
- No staged traffic split in the CD pipeline — deploys go from 0% to 100% in one step.
- Rollback requires re-deploy — no instant abort mechanism during a risky rollout.

## Why

Canary deployments limit the blast radius of a bad release. By routing 5–10% of production traffic
to the new version first, a regression affects only that fraction of users. Automated analysis
(error rate, latency) detects the regression and triggers rollback — often before any user reports
it. The remaining 90–95% of users are never affected.

The name comes from the "canary in a coal mine" concept: the canary (small traffic slice) detects
danger before the full population is exposed.

## Remediate

1. **Use Argo Rollouts with canary strategy** (recommended for Kubernetes):
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Rollout
   spec:
     strategy:
       canary:
         steps:
         - setWeight: 5      # 5% to canary
         - pause: {duration: 5m}
         - analysis:
             templates:
             - templateName: success-rate
         - setWeight: 20
         - pause: {duration: 10m}
         - setWeight: 100
   ```

2. **Define `AnalysisTemplate` with success criteria:**
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: AnalysisTemplate
   metadata:
     name: success-rate
   spec:
     metrics:
     - name: success-rate
       interval: 1m
       successCondition: result[0] >= 0.99
       failureLimit: 3
       provider:
         prometheus:
           address: http://prometheus:9090
           query: |
             sum(rate(http_requests_total{status!~"5.."}[2m]))
             / sum(rate(http_requests_total[2m]))
   ```
   Adjust thresholds: error rate <1%, P99 latency within 20% of baseline.

3. **Use Flagger as an alternative** to Argo Rollouts. Flagger integrates with Istio, Linkerd, or
   NGINX and performs metric analysis automatically. Configure a `Canary` CRD pointing at the
   Deployment and your metrics backend.

4. **Route a meaningful traffic percentage.** 5% is a good starting weight:
   - Large enough to generate statistically significant signal (e.g., if you handle 10,000 req/min,
     5% = 500 req/min — enough for reliable error rate measurement).
   - Small enough that a bad deploy only affects 5% of users.
   At very low traffic (<100 req/min), canary analysis is unreliable — use blue-green instead.

5. **Ensure the canary is compatible with the stable version's DB schema.** Both versions run
   simultaneously and share the same database. The canary version must work with the current schema.
   Use expand-contract migrations (see `backend/expand-contract-migrations`) before deploying a
   canary that requires schema changes.

6. **Set an auto-rollback trigger.** Argo Rollouts aborts and rolls back automatically when the
   `AnalysisRun` fails. Flagger does the same. Never rely on manual monitoring for canary analysis
   in an automated pipeline.

7. **Notify on canary events.** Configure Argo Rollouts or Flagger to send notifications (Slack,
   PagerDuty) on: canary started, canary promoted, canary aborted. Include the reason for abort.

## References

- Argo Rollouts documentation: Canary Deployments, AnalysisTemplate
- Flagger documentation (flagger.app)
- Google SRE Workbook: Progressive Rollouts
- DORA: Deployment frequency and change failure rate metrics
