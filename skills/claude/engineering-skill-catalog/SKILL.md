---
name: engineering-skill-catalog
description: Retrieve the right software-engineering technique for any backend, frontend, infra, QA, security, data, or craft task. Queries the OSE RAG catalogue (90+ skills) on demand — zero startup cost.
---

# Engineering Skill Catalog

This skill covers the full software-engineering stack: backend, frontend, infra/SRE, QA/testing, security, data/AI, and cross-cutting craft. The catalogue lives at `skills/catalog/` in the `agent-engineering-standard` repo and is served via the `opencode-search` MCP RAG engine.

## When to use

Invoke whenever you encounter a specialized engineering task: fixing an N+1 query, writing an SLO policy, hardening against OWASP A01 broken access control, writing contract tests, adding OpenTelemetry instrumentation, or any other domain-specific technique.

## How to retrieve a skill

**Primary (OSE MCP available):**
```
search("<describe the task>", scope="all", project_paths=["/home/hafiz/git/github.com/fairyhunter13/agent-engineering-standard"])
```
or for multi-skill context:
```
ask("<describe the task>", project_paths=["/home/hafiz/git/github.com/fairyhunter13/agent-engineering-standard"])
```
Read the top result(s) by `rerank_score`. Apply the **Remediate** section.

**Fallback (OSE daemon down / timeout):**
```
find /home/hafiz/git/github.com/fairyhunter13/agent-engineering-standard/skills/catalog -name "*.md" | xargs grep -l "<keyword>"
```
Then `Read` the matching file(s).

## Scope

Software-engineering tasks only. Do not use this catalogue for non-engineering queries.

## Catalogue disciplines

- **backend** — queries, transactions, caching, APIs, messaging, resilience, migrations, observability
- **frontend** — a11y, Core Web Vitals, bundle budget, SSR/RSC, state, i18n, CSP, RUM
- **infra** — IaC, containers, K8s, SLOs, error budgets, OpenTelemetry, CI/CD, DORA, zero-downtime
- **qa** — test pyramid, flaky tests, contract testing, property-based, mutation, coverage
- **security** — OWASP Top 10 (2025), injection, secrets, zero-trust, SAST/DAST/SCA, SBOM
- **data** — pipeline idempotency, schema evolution, PII, quality, partitioning, RAG eval, prompt injection
- **craft** — concurrency, error taxonomy, dependency hygiene, feature flags, debugging, code review, PRs
