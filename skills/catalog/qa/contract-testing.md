---
name: contract-testing
description: Use consumer-driven contract tests (Pact) to verify service API compatibility at the boundary without requiring full integration environments.
discipline: qa
tags: [testing, contracts, pact, microservices, api]
---

# Contract Testing

## When to use
Apply this skill when multiple services communicate via HTTP or async messaging; when integration tests are slow because they require all services to be running simultaneously; when an API provider change breaks consumers in staging but not in the provider's own CI; or when you need to decouple service release cadences.

## Signal
- Integration test environment outage blocks all PR merges.
- An API change by Team A breaks Team B's service, discovered only in staging.
- Integration tests require spinning up 5+ services to test a 2-service interaction.
- Provider team is unaware of what fields each consumer actually uses.
- API version negotiations happen via Slack/email rather than automated checks.
- Consumer teams are afraid to deploy the provider because they don't know what breaks.

## Why
Contract testing is the highest-ROI test type in microservice architectures. A contract defines exactly what a consumer requires from a provider — the fields it reads, the HTTP methods it calls, the response shapes it expects. The provider verifies the contract against its actual implementation. This catches API breaking changes at the source (provider CI) before they propagate to consumers, without requiring a shared integration environment. Consumer-driven contracts invert the traditional approach: instead of the provider guessing what consumers need, consumers declare their requirements precisely.

## Remediate

1. **Choose your contract testing tool.** For HTTP: **Pact** (multi-language, most mature). For async messaging: **Pact Async** or **AsyncAPI** contract linting. For GraphQL: **Pact with GraphQL matchers** or **GraphQL schema contracts**.

2. **Consumer writes the contract.** The consumer team writes a test that exercises the HTTP call and captures the request/response pair as a contract file (a Pact JSON file):
   ```ts
   // Consumer test (TypeScript / Jest)
   import { PactV3, MatchersV3 } from '@pact-foundation/pact';

   const provider = new PactV3({ consumer: 'OrderService', provider: 'UserService' });

   it('gets a user by ID', () => {
     provider.addInteraction({
       uponReceiving: 'a request for user 123',
       withRequest: { method: 'GET', path: '/users/123' },
       willRespondWith: {
         status: 200,
         body: {
           id: MatchersV3.integer(123),
           email: MatchersV3.string('user@example.com'),
           // Note: only declare fields the consumer actually uses
         },
       },
     });
     return provider.executeTest(async (mockServer) => {
       const user = await fetchUser('123', mockServer.url);
       expect(user.email).toMatch(/@/);
     });
   });
   ```
   This produces `pacts/OrderService-UserService.json`.

3. **Publish the contract to Pact Broker.** After the consumer test passes, publish the Pact file to a Pact Broker (self-hosted or PactFlow SaaS):
   ```sh
   npx pact-broker publish ./pacts \
     --consumer-app-version=$(git rev-parse HEAD) \
     --broker-base-url=https://pactbroker.example.com \
     --broker-token=$PACT_BROKER_TOKEN
   ```

4. **Provider verifies the contract in its CI.** The provider team adds a contract verification step to their CI pipeline. It replays the consumer's interactions against the running provider and confirms the responses match:
   ```ts
   // Provider verification test
   const verifier = new Verifier({
     providerBaseUrl: 'http://localhost:3000',
     provider: 'UserService',
     pactBrokerUrl: 'https://pactbroker.example.com',
     publishVerificationResult: true,
     providerVersion: process.env.GIT_SHA,
   });
   await verifier.verifyProvider();
   ```

5. **Fail provider PRs that break any consumer contract.** Configure CI to gate deployment on `can-i-deploy`:
   ```sh
   npx pact-broker can-i-deploy \
     --pacticipant UserService \
     --version $(git rev-parse HEAD) \
     --to production
   ```
   If any consumer contract is failing, `can-i-deploy` returns a non-zero exit code and blocks the deploy.

6. **Scope contracts to real consumer usage.** Declare only the fields the consumer actually uses in responses — not the full provider schema. This gives the provider team the freedom to add new fields, rename unused fields, or restructure responses without breaking consumers.

7. **For async messaging.** Define message contracts where the consumer declares the expected message structure. The provider (message producer) verifies that its published messages conform to the contract:
   ```ts
   // Pact async message contract
   provider.addMessage({
     description: 'order placed event',
     content: {
       orderId: MatchersV3.string('ord_123'),
       total: MatchersV3.decimal(49.99),
     },
   });
   ```

8. **Integrate into the Definition of Done.** Any PR that changes a service's API must include: (a) an updated consumer contract if it is a consumer change, or (b) a passing provider verification if it is a provider change. Both must publish results to the Pact Broker.

## References
- Pact documentation (docs.pact.io)
- PactFlow — hosted Pact Broker with advanced features
- "Consumer-Driven Contracts: A Service Evolution Pattern" — Martin Fowler
- AsyncAPI specification (asyncapi.com)
