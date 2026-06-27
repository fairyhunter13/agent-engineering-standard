---
name: mutation-testing
description: Validate that tests actually catch defects by running mutation testing and targeting a mutation score above 70% on critical modules.
discipline: qa
tags: [testing, mutation, quality, coverage, verification]
---

# Mutation Testing

## When to use
Apply this skill when code coverage is high but bugs still reach production; when verifying test suite quality after a major refactor; when a team wants to know whether their tests provide real defect detection or just coverage inflation; or when setting up quality gates for critical business logic.

## Signal
- Code coverage exceeds 80% but production bugs are frequent in covered modules.
- A PR removes an assertion from a test, but CI stays green (the test was passing anyway).
- No mutation score baseline exists for critical modules.
- After a refactor, tests were updated but it is unclear whether they still verify the original behavior.
- Business-critical modules (pricing, authorization, payments) have no mutation test history.

## Why
Mutation testing is the gold standard for measuring test *effectiveness* (vs. coverage, which only measures *execution*). A mutation tool makes small, systematic code changes — flipping `>` to `>=`, changing `&&` to `||`, deleting a return statement, inverting a conditional — and then runs your tests against each mutant. If the tests fail, the mutant is "killed" (good — tests caught the defect). If the tests pass, the mutant "survived" (bad — the defect was not detected). Mutation score = killed / (killed + survived). A high mutation score means your tests would have caught these defect classes.

## Remediate

1. **Choose your mutation testing tool by language:**
   - Python: `mutmut` (simple, fast) or `cosmic-ray` (more strategies)
   - JavaScript/TypeScript: `Stryker` (stryker-mutator.io) — excellent VS Code integration
   - Java/Kotlin: `PIT` (pitest.org) — integrates with Maven/Gradle
   - .NET: `Stryker.NET`
   - Go: `go-mutesting`
   - Rust: `cargo-mutants`

2. **Run mutation testing on a critical module first.** Start small — pick your highest-value business logic module (pricing engine, authorization rules, discount calculator) and run mutation testing on it only:
   ```sh
   # Python / mutmut
   mutmut run --paths-to-mutate src/pricing/

   # JavaScript / Stryker
   npx stryker run --mutate src/pricing/**/*.ts

   # Java / PIT (Maven)
   mvn org.pitest:pitest-maven:mutationCoverage \
     -DtargetClasses=com.example.pricing.* \
     -DtargetTests=com.example.pricing.*Test
   ```

3. **Interpret the mutation report.** After the run, review surviving mutants:
   ```sh
   mutmut results  # shows surviving mutations with line numbers
   mutmut show 42  # shows the specific code change that survived
   ```
   Example surviving mutant:
   ```python
   # Original
   if total > 100:
       apply_discount(total, 0.1)
   # Mutant (survived): if total >= 100:
   # → Your tests never exercise the boundary at exactly total == 100
   ```

4. **Fix surviving mutants by adding targeted assertions — not by skipping them.** For each surviving mutant, write a new test that would catch that exact mutation:
   ```python
   def test_discount_applies_above_100_not_at_exactly_100():
       assert calculate_total(items_worth=99.99) == 99.99   # no discount
       assert calculate_total(items_worth=100.00) == 100.00  # boundary: no discount
       assert calculate_total(items_worth=100.01) == 90.009  # just above: discount
   ```
   Never use `# mutmut: skip` (or Stryker's `// Stryker disable`) except for generated code or intentionally untestable constructs.

5. **Set a mutation score threshold for critical modules.** Target ≥ 70% mutation score for business logic modules. Add to CI:
   ```json
   // stryker.config.json
   {
     "thresholds": { "high": 80, "low": 70, "break": 60 }
   }
   ```
   ```xml
   <!-- PIT Maven — fail build if mutation coverage below 70% -->
   <mutationThreshold>70</mutationThreshold>
   ```

6. **Run mutation testing in CI at the right cadence.** Mutation testing is slow (runs all tests N times, where N = number of mutants). Practical strategies:
   - **Incremental**: only mutate lines changed in the PR (Stryker supports this: `--since`).
   - **Nightly**: run full mutation suite on `main` branch nightly, report to dashboard.
   - **On critical modules only**: never run mutation testing on UI components or generated code — focus on pure business logic.

7. **Track mutation score over time.** Add the mutation score (alongside coverage %) to your quality dashboard. A decreasing mutation score on a module is a leading indicator that new code lacks adequate test coverage.

8. **Combine with property-based testing.** Property-based tests are excellent at killing many mutants automatically — a test that generates 500 random inputs is far more likely to catch an off-by-one mutant than a test with 3 hand-picked examples.

## References
- Stryker Mutator (stryker-mutator.io) — JS, Java, .NET
- PIT Mutation Testing (pitest.org) — Java
- mutmut (boxed/mutmut) — Python
- Richard Bradshaw / Rob Sabourin — "An Introduction to Mutation Testing"
