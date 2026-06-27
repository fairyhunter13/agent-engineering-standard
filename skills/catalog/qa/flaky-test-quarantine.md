---
name: flaky-test-quarantine
description: Detect, quarantine, and eliminate flaky tests to restore CI signal reliability and engineering trust.
discipline: qa
tags: [testing, flakiness, reliability, ci, quarantine]
---

# Flaky Test Quarantine

## When to use
Apply this skill when CI pipelines are routinely retried, when engineers dismiss red CI runs with "it's probably just flaky", when the same test oscillates between pass and fail on unchanged code, or when you are inheriting a legacy test suite with unknown reliability.

## Signal
- CI pipelines configured with `retry: 3` or similar — a mask over underlying flakiness, not a fix.
- Specific tests with pass rates below 99% on unchanged commits.
- Engineers habitually re-run CI without investigating the failure reason.
- Nightly builds show intermittent failures that differ between runs.
- `sleep(500)` or `time.sleep(1)` in test code — a smell of timing-dependent tests.
- Assertions on `new Date()` or `Math.random()` without deterministic seeding.

## Why
A flaky test is worse than no test. A test that sometimes passes and sometimes fails on identical code provides no reliable signal. Developers learn to ignore it, which means when the test starts failing due to a real bug, nobody investigates. The test suite becomes a "boy who cried wolf" — when the wolf is real, the alarm is ignored. Flaky tests also inflate CI time (retries), waste engineer time (investigating phantom failures), and erode psychological safety around making changes.

## Remediate

1. **Measure flake rate per test over 30 days.** Any test with > 1% failure rate on commits where the related code did not change is a flaky candidate. Most CI systems (GitHub Actions, CircleCI, Buildkite) provide test result history. Build a query:
   ```sql
   SELECT test_name, failures / runs AS flake_rate
   FROM test_runs
   WHERE code_sha = passing_sha
   GROUP BY test_name
   HAVING flake_rate > 0.01
   ORDER BY flake_rate DESC;
   ```

2. **Quarantine immediately.** Move flaky tests to a non-blocking suite tagged `@flaky` or `[Flaky]`:
   ```python
   @pytest.mark.flaky  # pytest-rerunfailures with max_runs=1 in the main suite
   def test_user_registration():
       ...
   ```
   ```ts
   // Jest
   test.skip('FLAKY: payment webhook', () => { ... });
   ```
   Run the flaky suite separately (nightly, not on PR) so it does not block deployments while investigation is underway.

3. **Root-cause within one sprint — categorize the flakiness type:**
   - **Timing dependency**: assertion fires before async operation completes. Fix: replace `sleep` with explicit `await expect(element).toBeVisible()` or a polling assertion.
   - **External service dependency**: test calls a real third-party API that has occasional downtime. Fix: mock at the HTTP boundary (WireMock, nock, httpretty, MSW).
   - **Shared state pollution**: test depends on order — a previous test mutates shared state (DB, singleton, global variable). Fix: reset state before each test; use transactions that roll back.
   - **Race condition**: concurrent operations in the test produce non-deterministic outcomes. Fix: synchronize explicitly, use event-driven assertions.
   - **Resource contention**: parallel tests contend on port numbers, file paths, or DB row IDs. Fix: use random ports, unique IDs per test, isolated DB schemas.

4. **Delete tests that cannot be fixed within 2 sprints.** A quarantined test that nobody fixes is dead weight. Hold a quarterly "flaky test review" and delete tests that have been quarantined for > 2 sprints. A deleted test is honest — a lying test is harmful. File a backlog item to replace the deleted test with a better-designed one.

5. **Prevent new flaky tests from entering CI.** Add a linting rule (custom ESLint rule or custom Semgrep rule) to flag:
   - `sleep` / `time.sleep` in test files.
   - `Math.random()` / `Date.now()` without a mock in test files.
   - Hard-coded port numbers in tests.
   - Missing `afterEach(() => jest.resetAllMocks())`.

6. **Use deterministic test IDs.** When tests create DB records or file paths, use deterministic IDs from the test name rather than sequential auto-increment or UUID:
   ```ts
   const userId = `test-user-${expect.getState().currentTestName.replace(/\s/g, '-')}`;
   ```

7. **Report flake rate in retros.** Track flake rate as a team metric (alongside test runtime) and review it monthly. Reducing flake rate from 5% to 0.1% across a 500-test suite is a measurable engineering quality improvement.

## References
- Google Testing Blog — "Flaky Tests at Google and How We Mitigate Them"
- Sam Lambert — "The Sad State of the Art of Flaky Tests"
- pytest-rerunfailures (pytest plugin)
- Playwright `--retries` documentation
