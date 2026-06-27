---
name: owasp-a04-insecure-design
description: Embed security into system design through threat modeling, least-privilege defaults, and business logic limits before implementation begins.
discipline: security
tags: [owasp, threat-modeling, design, security, architecture]
---

# OWASP A04: Insecure Design

## When to use
Apply this skill when designing new features or systems (before implementation), during architecture review, during threat modeling sessions, or in post-incident analysis when a breach was caused by a design flaw rather than an implementation bug.

## Signal
- Security is considered only after a feature is fully implemented, as an afterthought.
- No threat model exists for a system handling sensitive data or financial transactions.
- Business logic allows unrestricted or unbounded actions: unlimited coupon redemption, unbounded file upload, no rate limiting on expensive operations.
- No abuse scenarios were considered during design (what happens if a malicious user...).
- Authorization and data validation rules exist only in the UI, not enforced server-side.
- "We'll add security later" appears in design documents or sprint planning.

## Why
A04:2025 is a distinct category from A02 (misconfiguration) and A06 (vulnerable components): it addresses flaws baked into the system's fundamental design that cannot be fixed by correct implementation alone. A correctly implemented but insecurely designed system can still be broken through business logic abuse, race conditions in financial flows, or missing rate limits on high-value actions. Insecure design requires redesign — not a security patch.

## Remediate

1. **Threat model every new system or significant feature before implementation.** Use the STRIDE methodology (Microsoft, 1999) to enumerate threats systematically:
   - **S**poofing: can an attacker impersonate another user or service?
   - **T**ampering: can an attacker modify data in transit or at rest?
   - **R**epudiation: can an actor deny performing an action (no audit trail)?
   - **I**nformation Disclosure: can sensitive data be exposed to unauthorized parties?
   - **D**enial of Service: can an attacker exhaust resources or disrupt availability?
   - **E**levation of Privilege: can an attacker gain capabilities they should not have?

   Threat modeling outputs: (a) a data flow diagram, (b) a list of threats per component, (c) mitigations for each threat. Use OWASP Threat Dragon or whiteboard + sticky notes.

2. **Design for least privilege from the start.** For each component, service, and user role, define the minimum permissions required. Ask: "What is the least access this component needs to perform its function?" Overpermissioned design is hard to restrict later without breaking functionality.

3. **Add business logic limits as design requirements.** Quantify limits at design time — not as "we might need to rate-limit this later":
   - Coupon redemption: max 1 per user per order, max 3 uses per coupon code.
   - File upload: max 50 MB per file, max 10 files per upload, virus scan required.
   - Financial transfers: max $10,000 per 24h without additional verification.
   - API calls: max 100 requests per minute per user.
   Document these as explicit acceptance criteria in the story.

4. **Fail securely by default.** Design every decision point to default to the most restrictive outcome:
   - Authentication check fails → deny access (not grant).
   - Authorization check throws an exception → deny access (not grant).
   - Feature flag check fails → disable feature (not enable).
   - External service returns unexpected response → reject (not proceed).

5. **Include security in the Definition of Done.** Every story must have security acceptance criteria:
   - What are the authorization requirements?
   - What inputs are validated? What is rejected?
   - What are the rate limits?
   - What events are logged?
   - Has a threat model been reviewed for new data flows?

6. **Design audit trails for sensitive operations.** Any operation that: modifies financial data, changes user roles, accesses sensitive records, or performs administrative actions must generate an immutable audit log entry. Design the log schema at design time — retrofitting audit logging is expensive and often incomplete.

7. **Consider abuse scenarios explicitly during design.** For each feature, ask "What happens if a malicious user tries to:
   - Submit the same form 1000 times?
   - Provide a 1 GB file where a small one is expected?
   - Exploit a TOCTOU (time-of-check/time-of-use) race condition in payment processing?
   - Reference other users' resources?
   - Exploit the feature for unintended purposes (discount stacking, referral fraud)?"
   Document each abuse scenario and its designed-in mitigation.

8. **Use secure design patterns.** Document these patterns in your architecture guide:
   - **Idempotency keys** for payment and financial operations (prevent duplicate charges).
   - **Optimistic locking** for concurrent resource modification.
   - **Signed URLs** for temporary access to private resources (not permanent public access).
   - **Separation of duties**: financial approval and financial execution by different roles.

## References
- OWASP A04:2021 – Insecure Design
- Microsoft STRIDE threat modeling methodology
- OWASP Threat Dragon (threat modeling tool)
- OWASP Application Security Verification Standard (ASVS)
- "The Art of Software Security Assessment" — Dowd, McDonald, Schuh
