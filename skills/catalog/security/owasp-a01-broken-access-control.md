---
name: owasp-a01-broken-access-control
description: Prevent IDOR, privilege escalation, and missing authorization by implementing default-deny access control at the framework layer.
discipline: security
tags: [owasp, access-control, authorization, security, api]
---

# OWASP A01: Broken Access Control

## When to use
Apply this skill when adding authorization to new API endpoints, when auditing an existing codebase for IDOR (Insecure Direct Object Reference) or privilege escalation vulnerabilities, when doing threat modeling for a multi-tenant application, or after a security incident involving unauthorized data access.

## Signal
- A user can access another user's data by incrementing an ID in the URL: `GET /api/invoices/1234` → works even for invoice belonging to user 999.
- Admin-only endpoints return data for non-admin users when the role header is omitted.
- Authorization logic duplicated ad hoc in some endpoints but missing in others.
- Client-provided user ID or role is used in the server-side access control decision without re-verification.
- `GET` endpoints (perceived as read-only) have no authorization check — mutations can be performed via parameter tampering.

## Why
A01:2025 is the most common web security vulnerability and moved to #1 in OWASP's 2021 Top 10 (from #5 in 2017). Broken access control allows unauthorized actors to: view other users' personal data, perform actions as another user (account takeover), escalate privileges from member to admin, or access tenant data in multi-tenant systems. Many IDOR vulnerabilities are trivially exploitable — just change a numeric ID in the URL — and lead to data breaches that trigger GDPR notifications.

## Remediate

1. **Establish a default-deny authorization policy.** Every endpoint must require explicit authorization. An unauthenticated or unauthorized request must return 401 or 403 by default. Apply this at the framework layer (middleware/interceptor), not per-endpoint:
   ```ts
   // Express.js — global auth middleware
   app.use(requireAuthentication); // applies to all routes
   app.use(requireAuthorization);  // role/permission check per route

   // Make exceptions explicit, not the rule
   app.get('/health', skipAuth, healthCheckHandler);
   ```

2. **Re-fetch owned resources from DB using authenticated user's context.** Never trust client-provided IDs to determine ownership. Always query the DB with a filter on `owner_id = current_user.id`:
   ```ts
   // Bad — trusts the client-provided ID without ownership check
   const invoice = await db.invoices.findById(req.params.id);

   // Good — enforces ownership at query level
   const invoice = await db.invoices.findFirst({
     where: {
       id: req.params.id,
       userId: req.user.id,  // enforced in the query, not checked after
     },
   });
   if (!invoice) throw new ForbiddenError('Access denied');
   ```

3. **Implement RBAC (Role-Based Access Control) or ABAC at the framework layer.** Use a well-established authorization library rather than ad hoc `if (user.role === 'admin')` checks scattered across handlers:
   - **Node.js**: `casl`, `accesscontrol`
   - **Python**: `fastapi-permissions`, `django-guardian`
   - **Java**: Spring Security
   - **Go**: Casbin
   Apply authorization policies as decorators/middleware, not inline in business logic.

4. **Scope all queries in multi-tenant systems.** In multi-tenant applications, every DB query must include a tenant filter:
   ```ts
   // Bad — returns data for all tenants
   const orders = await db.orders.findMany();

   // Good — scoped to current tenant
   const orders = await db.orders.findMany({
     where: { tenantId: req.tenant.id },
   });
   ```
   Consider a DB-level Row-Level Security (Postgres RLS) policy as a defense-in-depth measure.

5. **Validate authorization on resource mutations, not just reads.** PUT, PATCH, DELETE endpoints must check ownership before modifying. A common bug: GET checks ownership but POST/PUT does not:
   ```ts
   // Check ownership before update
   const existing = await db.posts.findFirst({ where: { id, authorId: userId } });
   if (!existing) throw new ForbiddenError();
   await db.posts.update({ where: { id }, data: body });
   ```

6. **Log and alert on 403 responses.** A high rate of 403 responses from a single IP or user is a strong signal of IDOR probing. Alert when: > 10 403 responses per minute from a single IP, or > 50 403 responses per session.

7. **Include IDOR test cases in security test suite.** For every API endpoint that returns user-specific data, write a security test that verifies cross-user access is rejected:
   ```ts
   it('rejects access to another user\'s invoice', async () => {
     const [alice, bob] = await createUsers(2);
     const aliceInvoice = await createInvoice({ userId: alice.id });
     const response = await api.get(`/invoices/${aliceInvoice.id}`)
       .setAuth(bob.token);
     expect(response.status).toBe(403);
   });
   ```

8. **Enforce function-level access control, not just UI-level.** Never hide a button in the UI as the sole access control mechanism. The API endpoint must enforce authorization independently of whether the UI exposes the action.

## References
- OWASP A01:2021 – Broken Access Control
- OWASP Testing Guide — Testing for IDOR (OTG-AUTHZ-004)
- OWASP Cheat Sheet — Authorization Cheat Sheet
- Casbin (casbin/casbin) — authorization library
