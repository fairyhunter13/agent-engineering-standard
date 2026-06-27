---
name: mock-boundaries
description: Mock only at system boundaries to maintain test fidelity, and use real infrastructure for integration tests to catch real integration bugs.
discipline: qa
tags: [testing, mocking, integration, unit, boundaries]
---

# Mock Boundaries

## When to use
Apply this skill when deciding whether to mock a dependency, when mock-heavy test suites are passing while real integrations break in staging, or when integration tests are so slow or brittle that the team has started mocking everything including the DB.

## Signal
- Tests mock the database ORM, but production SQL migrations fail with schema errors not caught in tests.
- A mocked HTTP client diverges from the real API's response structure — tests pass, production breaks.
- `MagicMock()` / `jest.mock()` used for every dependency including the class under test.
- Integration test suite mocks so many layers that it is effectively testing mock objects, not real code.
- A test that mocks `stripe.createPaymentIntent` is passing while `stripe.confirmPaymentIntent` (which exists in production) has never been called in tests.

## Why
Mocks are a tradeoff: they make tests fast and isolated, but they only catch bugs if they accurately model the real behavior of the dependency. When a mock diverges from reality — and this divergence is invisible without a real integration test — the mock creates a false sense of safety. "All tests pass" means nothing if the tests are testing against a fiction. The key insight: mock at the *system boundary* (where your code meets something you do not own), not at arbitrary internal points.

## Remediate

1. **Define what "boundary" means for your system.** System boundaries are the seams between your code and things you do not control:
   - **External HTTP APIs** (Stripe, Twilio, GitHub API, internal microservices you do not own).
   - **Database / data store** (Postgres, Redis, S3, Elasticsearch).
   - **Message queues / event streams** (Kafka, RabbitMQ, SQS).
   - **Filesystem** (if the path is not controlled by your test).
   - **System clock / random** (non-determinism sources).
   Everything *internal* to your service (other classes, modules, pure functions) should generally not be mocked.

2. **Unit tests: mock only system boundaries.** When testing a business service class, mock the DB repository and the HTTP client — not internal helper methods:
   ```ts
   // Good — mocking at the system boundary
   const mockRepo = { findUser: jest.fn().mockResolvedValue({ id: 1, email: 'u@test.com' }) };
   const mockEmailClient = { send: jest.fn().mockResolvedValue(undefined) };
   const service = new UserService(mockRepo, mockEmailClient);

   // Bad — mocking internal methods of the class under test
   jest.spyOn(service, 'internalValidationHelper').mockReturnValue(true);
   ```

3. **Integration tests: use real infrastructure.** For tests that verify DB query correctness, HTTP handler behavior, or message queue integration, use real dependencies via Testcontainers:
   ```python
   # pytest + testcontainers
   from testcontainers.postgres import PostgresContainer

   @pytest.fixture(scope='session')
   def postgres():
       with PostgresContainer('postgres:16') as pg:
           engine = create_engine(pg.get_connection_url())
           Base.metadata.create_all(engine)
           yield engine

   def test_find_user_by_email(postgres):
       with Session(postgres) as session:
           session.add(User(email='test@example.com'))
           session.commit()
           found = UserRepo(session).find_by_email('test@example.com')
           assert found.email == 'test@example.com'
   ```
   This catches schema mismatches, missing indexes, and query errors that mocks cannot.

4. **Never mock the thing under test.** If you are testing `OrderService`, do not mock `OrderService` itself or its private methods. You are testing its real behavior. Mocking it produces tautological tests that verify nothing.

5. **For external HTTP: use recorded responses or contract stubs.** Hand-written fake JSON responses for external APIs drift over time:
   - **VCR/Polly**: record real HTTP interactions once, replay them in tests. The recording is the source of truth.
   - **Contract stubs**: if using Pact, the consumer contract generates a stub server that accurately reflects what the consumer expects. Provider changes that break the contract are caught.
   - Avoid maintaining large `__fixtures__/stripe-response.json` files by hand — they become stale.

6. **Test the mock setup assumptions.** When a mock is used, add a separate integration test (perhaps in a slower suite) that makes a real call to the dependency and verifies the mock's assumptions are still correct. This is especially important for third-party APIs that version their responses.

7. **Identify over-mocked tests by "what am I actually testing?"** When you look at a test, ask: "If I removed all the mocks, what real code would execute?" If the answer is "very little" or "just orchestration calls to mocks," the test is likely over-mocked and provides minimal value. The code paths that actually do the work should be tested with real or near-real dependencies.

8. **Prefer dependency injection to enable real or mock injection.** Code that uses DI (constructor injection, function parameter injection) is easy to test with real or mock dependencies. Code that instantiates dependencies directly (`new StripeClient()` in a business method) is hard to test without monkey-patching.

## References
- Ian Cooper — "TDD, Where Did It All Go Wrong?" (DDD Europe 2017, YouTube)
- Martin Fowler — "Mocks Aren't Stubs" (martinfowler.com)
- Testcontainers (testcontainers.com)
- Mock Service Worker / WireMock for HTTP boundary mocking
