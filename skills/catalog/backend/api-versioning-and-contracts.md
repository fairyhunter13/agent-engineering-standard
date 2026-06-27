---
name: api-versioning-and-contracts
description: Version APIs and maintain backward-compatible contracts so consumers can evolve at their own pace.
discipline: backend
tags: [api, versioning, contracts, backward-compatibility, rest, grpc]
---

# API Versioning and Contracts

## When to use

Introducing breaking API changes while existing consumers are live. Multiple consumers operate on
different release cycles and cannot all upgrade simultaneously. Evolving a gRPC or Protobuf schema.
Renaming, removing, or changing the type of an existing field. Any change that would break a
consumer running the current version.

## Signal

- Consumer 4xx/5xx spikes immediately after a backend API release — the change broke the field
  contract that existing clients relied on.
- No version indicator in the URL path or `Accept` header — any change is implicitly breaking.
- Fields removed or renamed without a transition period.
- Client teams report their apps are broken by a backend deploy they were not told about.
- No contract tests between producer and consumer — regressions are discovered in production.

## Why

Unversioned breaking changes force all consumers to update simultaneously. In practice this is
impossible with independent teams, third-party integrations, or mobile apps where users have not
updated. API versioning decouples the producer's release cycle from the consumer's, giving consumers
time to migrate while the old contract remains live.

Backward compatibility is cheaper to maintain incrementally — one field at a time using the
expand-contract pattern — than to manage a big-bang version cut. Neglecting it creates surprise
outages and erodes trust with consumers.

## Remediate

1. **Add a version to the URL path or `Accept` header on day one.**
   - URL path: `/v1/users`, `/v2/users` — simple, cacheable, easy to route.
   - Header versioning: `Accept: application/vnd.myapi+json; version=2` — cleaner URL, harder to
     test in a browser.
   Choose one strategy and apply it consistently. URL path versioning is the pragmatic default.

2. **Use the expand-contract pattern for field changes.** Never rename or remove in a single deploy.
   The three-phase sequence:
   - **Expand**: add the new field alongside the old. Both fields are populated; new consumers can
     adopt the new field while old consumers continue using the old.
   - **Migrate consumers**: update all consumers to read and write the new field. Allow ≥2 release
     cycles (or calendar weeks).
   - **Contract**: remove the old field once no consumer reads it. Verify via consumer-driven
     contract tests before removal.

3. **For gRPC / Protobuf:**
   - Never reuse a field number after removing a field. Use the `reserved` keyword:
     `reserved 3; reserved "old_field_name";`
   - Add new fields with new numbers. Old clients ignore unknown fields (forward compatibility).
   - Mark deprecated fields with the `[deprecated = true]` option; remove in the next major version.

4. **Publish deprecation notices in response headers.** Use the IETF-standardized headers:
   ```
   Deprecation: true
   Sunset: Sat, 31 Dec 2025 23:59:59 GMT
   Link: <https://docs.example.com/migration>; rel="deprecation"
   ```
   Log consumer requests that use deprecated fields so you know when it is safe to remove them.

5. **Write consumer-driven contract tests.** Use Pact or a similar CDC framework. Consumer teams
   publish contracts describing what they expect; the producer's CI runs these contracts against
   every build. A breaking change fails the producer's pipeline before reaching production.

6. **Document the version lifecycle.** Maintain a public changelog and deprecation timeline. Give
   consumers at minimum 3 months' notice before sunset. Alert them via the `Deprecation` header, in
   API changelogs, and through direct communication for high-traffic consumers.

7. **Version gateways independently from business logic.** A thin versioning adapter layer
   transforms v1 wire format to v2 internal format. Keep version-specific shims out of core business
   logic.

## References

- Stripe API versioning strategy (stripe.com/blog)
- IETF RFC 8594: The Sunset HTTP Header Field
- Pact: Consumer-Driven Contract Testing (pact.io)
- Google API Design Guide: Versioning
