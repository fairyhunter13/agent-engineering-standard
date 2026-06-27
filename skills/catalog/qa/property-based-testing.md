---
name: property-based-testing
description: Use property-based testing to generate hundreds of randomized inputs and find edge cases that hand-written example tests miss.
discipline: qa
tags: [testing, property-based, hypothesis, quickcheck, fuzzing]
---

# Property-Based Testing

## When to use
Apply this skill for pure functions with wide input domains — parsers, serializers, encoders/decoders, data transformations, business rule validators, and math-heavy computations. Also apply when a production bug was caused by an input combination that was never thought of during test design, suggesting the input space is under-explored.

## Signal
- Function has more than 3–4 conditional branches over a large, continuous input space.
- Production bugs have been found at numeric boundaries (0, -1, MAX_INT, empty string, null).
- Example tests feel incomplete — "I could write these forever but still miss edge cases."
- Parsing or serialization logic where round-trip correctness is essential.
- Business rules (discounts, tax calculations, insurance scoring) with complex eligibility conditions.

## Why
Example-based tests check that `f(specific_input) == specific_output`. The engineer picks examples they thought of — which means they miss inputs they did not think of. Property-based testing (QuickCheck, 1999; Hypothesis, 2013) inverts this: the engineer states *invariants that must hold for all inputs*, and the framework generates hundreds of random inputs to try to falsify them. When a falsifying case is found, the framework *shrinks* it to the smallest possible input that still fails, producing a minimal reproducible counterexample.

## Remediate

1. **Choose your tool by language:**
   - Python: `hypothesis` (most mature PBT library in any language)
   - TypeScript/JavaScript: `fast-check`
   - Java/Kotlin: `jqwik`
   - Go: `gopter` or `testing/quick` (stdlib, limited)
   - Rust: `proptest`
   - Haskell/Erlang/Elixir: QuickCheck (original and ports)

2. **Start with the simplest property: round-trip correctness.** For any encode/decode, serialize/parse, or compress/decompress pair:
   ```python
   from hypothesis import given, strategies as st

   @given(st.text())
   def test_json_round_trip(s: str):
       assert json.loads(json.dumps(s)) == s

   @given(st.binary())
   def test_base64_round_trip(data: bytes):
       assert base64.b64decode(base64.b64encode(data)) == data
   ```

3. **Express domain invariants as properties.** Think about what must *always* be true regardless of input:
   - **Idempotency**: `f(f(x)) == f(x)` (normalizing a string, deduplicating a list)
   - **Associativity/commutativity**: order of operations should not matter (combining totals)
   - **Range bounds**: output is always within expected range (0 ≤ score ≤ 100)
   - **No crash**: function never raises an unhandled exception on any valid input
   - **Monotonicity**: larger input produces larger (or equal) output
   ```ts
   // fast-check
   fc.assert(
     fc.property(fc.integer({ min: 0, max: 10000 }), (price) => {
       const discounted = applyDiscount(price, 0.1);
       return discounted >= 0 && discounted <= price;
     })
   );
   ```

4. **Define domain-specific generators (strategies).** For complex domain objects, compose generators:
   ```python
   from hypothesis import strategies as st

   valid_email = st.emails()
   valid_age = st.integers(min_value=18, max_value=120)
   valid_user = st.builds(User, email=valid_email, age=valid_age)

   @given(valid_user)
   def test_user_validation_always_succeeds_on_valid_input(user: User):
       result = validate_user(user)
       assert result.is_valid
   ```

5. **Save failing examples for regression.** When Hypothesis/fast-check finds a failing case, it stores it in a local database (`hypothesis/` directory). On subsequent runs, it replays the failing case first (before generating new ones). Always commit this database:
   ```sh
   git add .hypothesis/  # Hypothesis example database
   ```
   In fast-check, save the seed: `fc.assert(..., { seed: failingSeed, path: '0:0' })`.

6. **Mark known-bad inputs with explicit examples.** After a PBT run finds a bug, add it as a fixed example test too:
   ```python
   from hypothesis import given, example, strategies as st

   @given(st.text())
   @example('')        # empty string — found by PBT, kept as regression
   @example('\x00')    # null byte — found by PBT, kept as regression
   def test_slug_generator(text: str):
       slug = make_slug(text)
       assert re.match(r'^[a-z0-9-]*$', slug)
   ```

7. **Scope to pure functions — not for DB/HTTP tests.** Property-based testing is most effective for pure functions with no side effects. For boundary integrations (HTTP, DB), use example-based integration tests or contract tests instead. Mixing PBT with I/O introduces flakiness and slow test runs.

8. **Integrate into CI like unit tests.** PBT frameworks run in CI with a reproducible seed derived from the run ID, so failures are reproducible. Add to your standard test command — no special pipeline step needed:
   ```sh
   pytest tests/unit/  # Hypothesis runs alongside regular pytest tests
   npx jest           # fast-check runs inside Jest tests
   ```

## References
- Hypothesis documentation (hypothesis.readthedocs.io)
- fast-check documentation (fast-check.dev)
- John Hughes — "QuickCheck: A Lightweight Tool for Random Testing of Haskell Programs" (1999)
- Scott Wlaschin — "An Introduction to Property Based Testing" (fsharpforfunandprofit.com)
