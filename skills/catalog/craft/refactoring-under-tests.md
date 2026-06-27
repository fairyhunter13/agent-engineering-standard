---
name: refactoring-under-tests
description: Change code structure without changing behavior by establishing a test safety net before touching anything.
discipline: craft
tags: [refactoring, testing, legacy-code, tdd, safety]
---

# Refactoring Under Tests

## When to use
Improving the internal structure of code without changing its observable behavior; working with legacy code that has low or no test coverage; extracting a module from a monolith.
Apply this any time you are changing code whose existing behavior must be preserved.

## Signal
- A "simple" refactoring caused a regression that was discovered in production, not by tests.
- Engineers are afraid to touch a particular module — "it works, don't change it."
- Tests are coupled to implementation details: they test private methods, internal state, or specific call counts on mocks — and break whenever the internals change even when behavior is preserved.
- Refactoring and feature changes are mixed in the same commit, making it impossible to attribute regressions.
- "I refactored it and the tests still pass" cannot be said with confidence because there are no tests.
- The word "refactor" is used to mean "change the behavior while also restructuring" — the concepts are conflated.

## Why
Refactoring is by definition behavior-preserving structural change.
Without tests, you cannot verify that behavior was preserved — you are guessing.
Tests are the executable specification of what the code must do; refactoring is the technique of changing the code while keeping that specification satisfied.
Tests coupled to implementation (white-box tests) are worse than no tests for refactoring: they break every time you touch internals, creating false signals and slowing you down.
The safety net of black-box tests is what enables confident, fast structural improvement without fear.

## Remediate
1. **Characterization tests first**: before touching any code, write tests that document the current behavior — even if that behavior is wrong. Run them, verify they pass, commit them. Now you have a safety net. Michael Feathers calls these "characterization tests"; their purpose is not to assert correct behavior, but to detect any change in behavior during refactoring.
2. **Strangler Fig for large-scale restructuring**: build the new structure alongside the old code. Redirect traffic to the new path at a routing boundary (HTTP handler, interface implementation, dependency injection). When the new code handles all traffic correctly, delete the old code. No big-bang replacement.
3. **Extract → test → refactor cycle**: (a) extract the tangled logic into a named method or class with a clear interface; (b) test that extracted unit in isolation through its public interface; (c) now refactor the extracted unit freely — the test catches regressions. This is the "seam" concept from "Working Effectively with Legacy Code."
4. **Strict commit discipline**: refactoring commits must contain only structural changes — no behavior changes. If you spot a bug while refactoring, do not fix it in the same commit. Record it (TODO comment, issue), finish the refactor, then fix the bug in a separate commit with its own test. Mixing them makes bisect impossible.
5. **Test through the public API only**: tests must be black-box. They call the public interface and assert on observable outputs — return values, side effects on external collaborators (via mocks), or system state. Never test private methods, never assert on internal state fields, never couple to implementation choice. Black-box tests survive refactoring; white-box tests fight it.
6. **Baby steps with green at every commit**: each refactoring step (rename, extract, inline, move) should be small enough to complete in under 5 minutes and leave the test suite green. Commit after each green step. If you break tests, revert immediately rather than pushing through — a broken test suite is not a foundation for further refactoring.

## References
- "Refactoring: Improving the Design of Existing Code" — Martin Fowler (2nd edition, 2018)
- "Working Effectively with Legacy Code" — Michael C. Feathers (characterization tests, seams)
- "Test-Driven Development: By Example" — Kent Beck
- Strangler Fig Application pattern — Martin Fowler (martinfowler.com)
- "The Mikado Method" — Ola Ellnestam & Daniel Brolund (incremental refactoring technique)
