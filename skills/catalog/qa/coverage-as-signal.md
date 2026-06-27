---
name: coverage-as-signal
description: Use code coverage as a map for finding test gaps, not as a target to game — augment with branch coverage and mutation testing.
discipline: qa
tags: [testing, coverage, metrics, ci, quality]
---

# Coverage as Signal

## When to use
Apply this skill when coverage thresholds are being set for CI, when coverage reports are used as the primary measure of test quality, when coverage is gaming (trivial tests with no assertions inflating percentages), or when 90%+ coverage coexists with frequent production bugs.

## Signal
- A blanket 80% line coverage threshold applied across all modules regardless of criticality.
- Tests exist that execute code paths but have no assertions (`assert True` / `expect(true).toBe(true)`).
- Coverage report shows 95% coverage on the payment module, but a critical discount logic bug slipped through.
- Coverage threshold is being "met" by testing trivial getters/setters while complex business logic is untested.
- Removing an assertion in a test does not fail CI.
- No distinction between coverage of critical paths vs. boilerplate.

## Why
Coverage measures which *lines were executed* during tests, not which *behaviors were verified*. A test that calls a function but asserts nothing will show 100% coverage on that function while catching no bugs. High coverage is a necessary but not sufficient condition for a good test suite. The real danger is that teams mistake it for a sufficient condition — achieving the coverage threshold by any means (including tests without meaningful assertions) and then declaring the code "well tested."

## Remediate

1. **Use branch/path coverage, not just line coverage.** Line coverage tells you which statements were reached; branch coverage tells you whether both the `true` and `false` branches of every conditional were exercised. A function with `if (isPremium)` at 100% line coverage might have only tested the `true` branch:
   - Jest: `--coverage --coverageProvider=v8` reports branch coverage.
   - Python: `coverage run --branch` + `coverage report`.
   - Java: JaCoCo branch coverage.
   Target ≥ 80% branch coverage on business logic modules.

2. **Set per-module thresholds reflecting risk.** Not all code is equally critical. A payment processing module and a logging utility module should not share the same coverage threshold:
   ```json
   // Jest coverage thresholds by directory
   "coverageThresholds": {
     "./src/payments/": { "branches": 90, "lines": 95 },
     "./src/utils/": { "branches": 60, "lines": 70 },
     "global": { "lines": 75 }
   }
   ```

3. **Audit uncovered lines: dead code or untested risk?** View the detailed HTML coverage report (`lcov-report`) and click through uncovered lines. For each uncovered block, ask: "Is this dead code that should be deleted, or is this a real execution path that carries risk?" Dead code should be deleted. Risky untested code needs a test.

4. **Validate tests with mutation testing.** Mutation testing introduces small code changes (mutations) — flipping `>` to `>=`, removing a condition, changing a return value — and checks whether your tests catch them. If they don't, the test is not actually verifying the behavior:
   ```sh
   # Python
   mutmut run --paths-to-mutate src/payments/

   # JavaScript/TypeScript
   npx stryker run

   # Java
   mvn org.pitest:pitest-maven:mutationCoverage
   ```
   A mutation score of 70%+ on critical modules means tests are actually catching defects.

5. **Fail CI on coverage *regression*, not just absolute threshold.** An absolute 80% threshold can be gamed incrementally. A regression gate fails the build if coverage drops below the *current* committed baseline:
   ```sh
   # Generate baseline
   coverage json -o coverage-baseline.json
   # In CI, compare against baseline
   python scripts/check_coverage_regression.py coverage-baseline.json coverage.json
   ```
   Some tools (Codecov, Coveralls) provide this automatically via PR comments.

6. **Ban assertion-free tests.** Add a linting rule to catch tests with no assertions:
   ```js
   // ESLint rule: jest/expect-expect
   "jest/expect-expect": ["error", { "assertFunctionNames": ["expect", "assert*"] }]
   ```
   ```python
   # pylint or custom check: flag test functions with no assert/raise
   ```

7. **Use coverage as a map for sprint planning.** Pull the coverage report into your sprint review: which recently changed modules have the lowest branch coverage? Use this as an input to prioritizing test backlog items — not as a mandate to immediately write tests for everything.

8. **Communicate the right mental model.** In team retrospectives and onboarding, establish: "80% coverage means we have exercised 80% of lines — it does not mean the remaining 20% is safe or the 80% is well-verified. It is a starting signal, not a finish line."

## References
- Martin Fowler — "TestCoverage" (martinfowler.com/bliki/TestCoverage.html)
- mutmut (boxed/mutmut — Python mutation testing)
- Stryker Mutator (stryker-mutator.io)
- PIT Mutation Testing (pitest.org — Java)
- Codecov / Coveralls — coverage regression tracking
