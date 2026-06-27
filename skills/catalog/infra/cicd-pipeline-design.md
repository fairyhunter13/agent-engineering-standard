---
name: cicd-pipeline-design
description: Design a CI/CD pipeline that enforces quality gates, minimizes feedback latency, and enables multiple deployments per day safely.
discipline: infra
tags: [cicd, devops, deployment, quality-gates, dora]
---

# CI/CD Pipeline Design

## When to use

The pipeline is slow (>30 minutes end-to-end), flaky (fails randomly), or skips quality gates under
time pressure. Deploy frequency is low — deployments happen weekly rather than multiple times per
day. Change failure rate is high (>15% of deploys cause an incident). Engineers batch up many
changes into one large release to "amortize" deployment cost, amplifying risk.

## Signal

- Pipeline runtime >20 min before the first feedback on a PR.
- Developers comment out tests locally to get CI to pass faster.
- Flaky tests cause pipeline retries — obscuring real failures.
- Deploys are scheduled maintenance events rather than routine operations.
- DORA: deployment frequency <1/week; lead time >1 week; change failure rate >15%.
- No preview environments for PR review — reviewers cannot test changes live.
- Staging and production deployment steps are manually triggered by one person.

## Why

A slow, unreliable pipeline is a tax on every engineer on every change. Engineers batch multiple
changes to amortize deployment cost — but larger batches mean larger blast radius when something
goes wrong. Fast, reliable pipelines encourage small, frequent, low-risk deploys — the DORA
"elite" pattern associated with high organizational performance.

Quality gates enforce non-negotiable standards (test pass, lint clean, security scan) consistently.
Without gates, shortcuts taken under time pressure become permanent technical debt.

## Remediate

1. **Design a staged pipeline that fails fast.** Every stage should fail before proceeding to more
   expensive stages:
   ```
   Stage 1: Code quality     (<3 min)   lint, format, type-check
   Stage 2: Unit tests       (<5 min)   isolated, no external deps
   Stage 3: Integration      (<15 min)  DB, cache, downstream service mocks
   Stage 4: Build + scan     (<5 min)   Docker build, Trivy CVE scan
   Stage 5: Deploy staging   (<5 min)   helm upgrade --atomic to staging
   Stage 6: Smoke tests      (<5 min)   synthetic checks against staging
   Stage 7: Deploy production (<2 min)  with canary or rolling strategy
   ```
   Fail at Stage 1 (lint failure) within 3 minutes — not after 30 minutes of integration tests.

2. **Parallelize independent stages.** Unit tests, lint, and type checks have no dependencies on
   each other — run them in parallel:
   ```yaml
   # GitHub Actions example
   jobs:
     lint:      { ... }
     unit-test: { ... }
     type-check: { ... }
     integration-test:
       needs: [lint, unit-test, type-check]
   ```

3. **Enforce pipeline gates — never deploy on red.** Configure branch protection rules: PR merges
   require all required status checks to pass. No manual override for production deploys without an
   explicit runbook step.

4. **Fix flaky tests immediately.** A flaky test is a broken test. Quarantine flaky tests to a
   separate suite; fix or delete within 48 h. A pipeline that passes 80% of the time provides no
   reliable quality signal.

5. **Provision ephemeral preview environments for each PR.** Tools: Kubernetes namespaces with
   Helmfile, Vercel preview deployments, Railway PR environments. Reviewers test changes in a live
   environment before merging. Environments are deleted when the PR closes.

6. **Automate production promotion.** Production deploys should be triggered by merging to main, not
   by manual action. Use a GitOps tool (Argo CD, Flux) to keep production in sync with the main
   branch. Manual steps create bottlenecks and knowledge silos.

7. **Measure DORA metrics and build a dashboard.** At minimum:
   - **Deploy frequency**: events from your CD tool per day/week.
   - **Lead time**: PR open timestamp → production deploy timestamp.
   - **Change failure rate**: % of deploys that trigger rollback or hotfix within 1 hour.
   - **MTTR**: incident start → resolution timestamps.
   Target elite tier: deploy multiple times/day, lead time <1 h, CFR <5%, MTTR <1 h.

8. **Cache dependencies and build artifacts.** Cache `node_modules`, Maven `.m2`, Go module cache,
   and Docker layer cache between pipeline runs. This alone can cut pipeline time by 50%.

## References

- DORA (DevOps Research and Assessment): State of DevOps report
- Accelerate: The Science of Lean Software and DevOps (Forsgren, Humble, Kim)
- GitHub Actions documentation: Caching, Parallel jobs
- Argo CD documentation: GitOps continuous delivery
