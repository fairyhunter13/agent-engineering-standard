---
name: test-pyramid
description: Balance test investment across unit, integration, and E2E layers to maximize defect detection speed and minimize CI cost.
discipline: qa
tags: [testing, unit, integration, e2e, test-pyramid]
---

# Test Pyramid

## When to use
Apply this skill when deciding how to test a new feature, when a CI suite is slow or fragile, when there are too many E2E tests relative to unit/integration, or when the team is trying to understand why bugs are escaping to production despite high test count.

## Signal
- E2E tests represent more than 20% of the total test suite.
- Unit tests represent less than 50% of the total test suite.
- CI pipeline takes more than 30 minutes end-to-end.
- Suite fails flakily without code changes (often caused by over-reliance on E2E).
- Most bugs are caught in production or staging, not in CI.
- Engineers re-run CI without investigating failures ("it'll pass on retry").

## Why
The test pyramid (Mike Cohn, 2009; affirmed by Google Testing Blog and DORA research) encodes an empirical insight: unit tests are cheap to write, fast to run, and have precise failure signals; E2E tests are expensive to write, slow to run, and have noisy failure signals. The optimal distribution for most applications in 2026 is approximately 70% unit, 20% integration, and 10% E2E. Inverting this — the "ice cream cone anti-pattern" — produces a slow, brittle CI that developers stop trusting.

## Remediate

1. **Audit your current distribution.** Count tests by type. A rough mapping:
   - Unit (Google "Small"): no I/O, runs in < 1 ms, tests a single function/class.
   - Integration (Google "Medium"): tests a boundary — DB query, HTTP handler, queue consumer. May use real infrastructure.
   - E2E (Google "Large"): drives a real browser or CLI against a running environment.
   If E2E > 20%, find which user journeys have duplicate coverage at lower levels.

2. **Target ≥ 70% unit tests.** Unit tests should cover all business logic, pure functions, state machines, data transformations, and validation rules. They run in milliseconds, have zero infrastructure dependencies, and produce precise error messages. A 1000-test unit suite should complete in under 5 seconds.

3. **Target ~20% integration tests.** Integration tests verify real boundary behavior that mocks cannot faithfully simulate: SQL queries against a real DB schema, HTTP request/response shapes, message broker serialization. Use test containers (Testcontainers library) for real Postgres/Redis/Kafka in CI without a shared environment.

4. **Target ≤ 10% E2E tests.** E2E tests should cover only the critical user journeys whose value is high enough to justify their cost: user registration, login/logout, checkout, payment, document upload. These are the flows where no other test layer catches end-to-end wiring failures.

5. **Ask "where do our bugs actually come from?"** Run a defect origin analysis on the last quarter's bugs. If most originate from: (a) business logic errors → add unit tests; (b) DB query bugs → add integration tests; (c) full-stack wiring → add E2E for that specific journey. Let bug origin data drive investment.

6. **Write tests at the lowest sufficient level.** Before writing an E2E test, ask: could this be a unit test of the business logic + a contract test of the API boundary? If yes, prefer those two. E2E tests for things that unit tests can cover are a maintenance tax with no added coverage value.

7. **Parallelize integration and E2E tests.** Use test sharding (`--shard=1/4`, Playwright's `--workers`) to run slow tests in parallel. Set a CI timeout: unit tests ≤ 2 min, integration ≤ 10 min, E2E ≤ 30 min. Tests that exceed these budgets are candidates for refactoring or removal.

8. **Add contract tests at service boundaries.** Between unit and integration, contract tests (Pact) verify that service A and service B agree on the API contract without requiring both to run. They belong at the upper end of the integration layer.

## References
- Mike Cohn — "Succeeding with Agile" (test pyramid origin)
- Google Testing Blog — "Just Say No to More End-to-End Tests"
- DORA Accelerate State of DevOps Report
- Martin Fowler — Test Pyramid (martinfowler.com/bliki/TestPyramid.html)
