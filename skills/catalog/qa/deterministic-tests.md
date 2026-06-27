---
name: deterministic-tests
description: Eliminate sources of non-determinism (time, randomness, ordering, external I/O) from tests to make CI reliable and reproducible.
discipline: qa
tags: [testing, determinism, reproducibility, ci, reliability]
---

# Deterministic Tests

## When to use
Apply this skill when tests pass locally but fail in CI; when tests fail in one execution order but pass in another; when a test depends on the current time, random numbers, or live network responses; or when debugging a test that "should be passing" but occasionally fails.

## Signal
- `datetime.now()`, `Date.now()`, `time.time()`, or `clock.instant()` called inside the system under test without injection.
- `Math.random()` / `random.random()` used in test subjects or in test setup without a fixed seed.
- Test fails when run in isolation but passes when the full suite runs (order dependency).
- Network calls in tests without stubs — tests fail when the third-party API is down.
- `os.getenv('DATABASE_URL')` points to a shared environment in CI.
- Test assertions check for "approximately now" with a time window (e.g., `createdAt >= now - 5s`).

## Why
Non-deterministic tests produce both false negatives (test fails on correct code) and false positives (test passes on broken code because the random input happened to be valid). They waste engineering time, break CI pipelines, and ultimately cause developers to distrust the test suite. The core principle is simple: given the same inputs, a test must always produce the same output.

## Remediate

1. **Freeze time — inject a clock.** Never call `datetime.now()` or `Date.now()` directly in code that is under test. Instead, inject a clock:
   ```python
   # Python — use freezegun
   from freezegun import freeze_time

   @freeze_time("2024-01-15 10:00:00")
   def test_invoice_due_date():
       invoice = Invoice.create(payment_terms_days=30)
       assert invoice.due_date == date(2024, 2, 14)
   ```
   ```ts
   // Jest
   beforeEach(() => jest.useFakeTimers({ now: new Date('2024-01-15T10:00:00Z') }));
   afterEach(() => jest.useRealTimers());
   ```
   ```java
   // Java — inject Clock
   Clock clock = Clock.fixed(Instant.parse("2024-01-15T10:00:00Z"), ZoneOffset.UTC);
   InvoiceService service = new InvoiceService(clock);
   ```

2. **Seed random number generators.** If randomness is unavoidable (e.g., sampling, shuffling), inject the PRNG and fix the seed in tests:
   ```python
   import random
   rng = random.Random(42)  # fixed seed — deterministic
   result = shuffle_items(items, rng=rng)
   ```
   ```ts
   // fast-check (property-based) — runs use reproducible seeds logged on failure
   fc.assert(fc.property(fc.integer(), (n) => fn(n) >= 0), { seed: 42 });
   ```

3. **Isolate DB state — reset before each test.** Tests that share a DB must not bleed state between them:
   - **Transactions**: wrap each test in a transaction and roll back after:
     ```python
     @pytest.fixture(autouse=True)
     def db_rollback(db):
         yield
         db.session.rollback()
     ```
   - **Test containers**: spin up a fresh DB per test suite run (CI-safe, no shared state).
   - **Truncate tables**: in `beforeEach`, truncate all relevant tables.
   Never share a DB between parallel test workers without schema-level isolation.

4. **Mock external HTTP calls — stub at the boundary.** Tests must not make real network calls:
   ```ts
   // msw (Mock Service Worker) — intercepts fetch/XHR at the network layer
   import { http, HttpResponse } from 'msw';
   const server = setupServer(
     http.get('https://api.stripe.com/v1/customers/:id', () =>
       HttpResponse.json({ id: 'cus_123', email: 'user@example.com' })
     )
   );
   beforeAll(() => server.listen());
   afterEach(() => server.resetHandlers());
   afterAll(() => server.close());
   ```
   Alternatives: VCR/Polly (record/replay), WireMock (Java), httpretty (Python), nock (Node.js).

5. **Eliminate test-order dependencies.** Run your test suite in random order to expose hidden ordering:
   ```sh
   pytest --randomly-seed=random  # pytest-randomly plugin
   jest --randomize              # Jest --randomize flag (v29+)
   ```
   When a test only passes in a specific order, the earlier test is leaking state (global variable, singleton, environment variable, file on disk). Fix by cleaning up in `afterEach`.

6. **Use unique resources per test.** Tests that share resource names (port numbers, file paths, DB row PKs) contend with each other in parallel runs:
   ```ts
   const port = await getRandomFreePort(); // not a hardcoded port
   const tmpDir = await fs.mkdtemp(os.tmpdir() + '/test-');
   ```

7. **Make environment explicit.** Tests should not depend on environment variables being set or unset by default. Set all required env vars explicitly in `beforeEach` and clear them in `afterEach`. Use `.env.test` files loaded explicitly by the test runner.

8. **Check UUID generation.** If your code generates UUIDs and tests assert on them, use a spy to return a predictable value rather than asserting a UUID pattern:
   ```ts
   jest.spyOn(crypto, 'randomUUID').mockReturnValue('00000000-0000-0000-0000-000000000001');
   ```

## References
- Martin Fowler — "Eradicating Non-Determinism in Tests" (martinfowler.com)
- freezegun library (spulec/freezegun)
- Mock Service Worker (mswjs.io)
- pytest-randomly plugin
- Testcontainers library
