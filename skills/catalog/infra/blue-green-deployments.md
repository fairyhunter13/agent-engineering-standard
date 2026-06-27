---
name: blue-green-deployments
description: Deploy new versions alongside old using blue-green to enable instant rollback and zero-downtime production releases.
discipline: infra
tags: [deployment, kubernetes, zero-downtime, rollback, devops]
---

# Blue-Green Deployments

## When to use

The team needs instant rollback capability (sub-minute, not minutes-long re-deploy). Mixed-version
traffic during a rolling update is unacceptable (e.g., API breaking changes that cannot be handled
with expand-contract during the rollout window). Smoke tests and synthetic checks must be validated
against the new version with production infrastructure before any live traffic is served.

## Signal

- Rolling updates cause mixed-version requests — old and new pods serve the same endpoint
  simultaneously during the rollout window.
- Rollback requires a re-deploy of the old version (10–15 min) rather than a switch.
- No pre-live validation window — new code goes live immediately on first pod readiness.
- Post-deploy incidents require rollback; current process is slow and stressful.

## Why

Blue-green maintains two complete, identically-provisioned environments: **blue** (current
production) and **green** (new version). Traffic flows to blue. Green is deployed, smoke-tested, and
validated with no live user traffic. When ready, a single load-balancer or Kubernetes Service
selector switch moves all traffic from blue to green — atomic, instant, and with no mixed-version
window.

Rollback is equally instant: switch the selector back to blue. The old environment remains live and
warm, waiting for exactly this scenario.

The trade-off: blue-green requires double the infrastructure during the transition window. For most
services, this is the right trade-off for high-availability requirements.

## Remediate

1. **On Kubernetes: use two Deployments with a Service selector switch.**
   ```yaml
   # Service with selector pointing to blue
   apiVersion: v1
   kind: Service
   metadata:
     name: myapp
   spec:
     selector:
       app: myapp
       slot: blue     # ← switch to "green" to cut over
   ---
   # Blue Deployment
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: myapp-blue
   spec:
     template:
       metadata:
         labels:
           app: myapp
           slot: blue
   ---
   # Green Deployment
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: myapp-green
   spec:
     template:
       metadata:
         labels:
           app: myapp
           slot: green
   ```
   Cutover: `kubectl patch service myapp -p '{"spec":{"selector":{"slot":"green"}}}'`

2. **Use Argo Rollouts with `strategy: blueGreen`** for a managed, GitOps-friendly implementation:
   ```yaml
   strategy:
     blueGreen:
       activeService: myapp-active
       previewService: myapp-preview
       autoPromotionEnabled: false  # require manual approval after smoke tests
   ```
   Argo Rollouts handles the Service switch and provides a promotion/abort CLI.

3. **Run smoke tests and synthetic checks against the green (preview) environment before promoting.**
   The green environment is accessible via the `previewService` before any live traffic hits it.
   Run your full smoke test suite against the preview URL. Only promote after passing.

4. **Monitor error rate for 5–15 minutes after cutover.** Watch: 5xx rate, P99 latency, saturation.
   Have a rollback decision threshold (e.g., error rate >1% for 2 consecutive minutes → auto-rollback
   or page on-call for manual rollback).

5. **Ensure the database schema is compatible with both versions.** Blue-green does not help if the
   new version's DB migration breaks the old version's reads. Use expand-contract migrations (see
   `backend/expand-contract-migrations`) so both versions work with the same schema.

6. **Clean up the old (blue) environment after a successful green promotion.** Scale blue to 0 after
   30–60 minutes of healthy green traffic. Keep the Deployment definition for fast rollback for
   another 24 hours, then delete.

7. **Consider costs.** Blue-green doubles compute costs during the transition window. For bursty
   traffic patterns, ensure the green deployment is fully scaled before cutover. Use spot/preemptible
   nodes for the old (blue) environment to reduce cost during the drain period.

## References

- Argo Rollouts documentation: Blue-Green Deployment
- Martin Fowler — BlueGreenDeployment (martinfowler.com)
- Kubernetes documentation: Deployments, Services
