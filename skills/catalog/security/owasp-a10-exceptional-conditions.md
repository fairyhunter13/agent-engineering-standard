---
name: owasp-a10-exceptional-conditions
description: Ensure exceptions cause secure failure modes — deny access on error, log all exceptions, and never expose internal details to clients.
discipline: security
tags: [owasp, error-handling, exceptions, security, resilience]
---

# OWASP A10: Exceptional Conditions (Server-Side Request Forgery / Logic Errors)

## When to use
Apply this skill when reviewing error handling in security-critical code paths (auth, authz, payment, data access), when designing fail-safe behavior for distributed systems, or during post-incident analysis where a logic error caused a security failure.

## Signal
- `except: pass` or bare `catch(e) {}` silently swallows exceptions in auth or authorization code.
- A service grants access when an authorization service returns an unexpected response (fails open).
- Error response messages expose internal details: stack traces, SQL queries, file paths, class names.
- Unhandled exceptions at the authorization layer result in HTTP 500 responses rather than 403.
- `try { authorize(user); } catch (e) { /* ignore error, proceed */ }` pattern in production.
- Chaos engineering reveals that the system grants access or processes transactions when dependencies are unavailable.

## Why
A10:2025 is a new OWASP category reflecting a class of vulnerabilities that prior Top 10 lists did not address explicitly: when exceptional conditions (errors, timeouts, unexpected responses) cause systems to fail in an insecure way. "Failing open" — granting access or completing an operation when the verification fails — is a catastrophic security error. A developer who writes `if (authz_check() == true) { allow }` and catches exceptions silently has effectively disabled authorization for any exception condition. This is not hypothetical: numerous production incidents have involved auth services timing out and applications defaulting to allow.

## Remediate

1. **Fail closed — deny access on any exception in security code.** Every authorization check must default to deny on failure, never to allow:
   ```ts
   // Bad — fails open on exception
   async function authorizeUser(user: User, resource: Resource): Promise<void> {
     try {
       const result = await authzService.check(user.id, resource.id);
       if (!result.allowed) throw new ForbiddenError();
     } catch (e) {
       if (e instanceof ForbiddenError) throw e;
       // Bug: other exceptions (timeout, parse error) proceed silently → access granted
     }
   }

   // Good — fails closed: any unexpected exception → deny
   async function authorizeUser(user: User, resource: Resource): Promise<void> {
     let result: AuthzResult;
     try {
       result = await authzService.check(user.id, resource.id);
     } catch (e) {
       logger.error('Authorization service failure', { error: e, userId: user.id, resourceId: resource.id });
       throw new ForbiddenError('Authorization check failed');  // deny on any error
     }
     if (!result.allowed) throw new ForbiddenError();
   }
   ```

2. **Never swallow exceptions silently.** A silent catch is a security and reliability hazard. Every caught exception must be:
   - Logged at ERROR level with full context (the exception, the user, the operation, the resource).
   - Either re-thrown, transformed into a safe error, or explicitly handled with documented rationale.
   ```python
   # Bad
   try:
       authorize(user, resource)
   except Exception:
       pass  # silent swallow

   # Good
   try:
       authorize(user, resource)
   except AuthorizationError:
       raise  # expected — re-raise
   except Exception as e:
       logger.error("Unexpected authorization error", exc_info=e, extra={"user_id": user.id})
       raise ForbiddenError("Authorization failed") from e  # deny, log, propagate safely
   ```

3. **Return generic error messages to clients; log details server-side.** Client-facing error responses must never expose:
   - Stack traces (exposes file paths, library versions, internal architecture).
   - SQL errors (exposes table names, column names, query structure — aids SQLi).
   - Internal IP addresses or service names.
   - Specific reasons for auth failure (username not found vs. wrong password → enumeration risk).
   ```ts
   // Generic client response
   res.status(401).json({ error: 'Authentication failed' });  // same message for all failure types

   // Detailed server log (never sent to client)
   logger.warn('Login failed', { reason: 'user_not_found', email, ip: req.ip });
   ```

4. **Distinguish expected from unexpected exceptions.** Design explicit exception hierarchies:
   - Expected: `ValidationError`, `ForbiddenError`, `NotFoundError`, `ConflictError` — handle and return appropriate HTTP codes.
   - Unexpected: anything else — log at ERROR, alert on-call, return HTTP 500 with generic message.
   Alert on unexpected exception rates. A spike in unexpected exceptions in an auth path is a security signal.

5. **Use circuit breakers for external security dependencies.** If your authorization depends on an external service (OPA, Keycloak, custom authz service), use a circuit breaker:
   - **Half-open**: after N failures, open the circuit (deny all requests, do not forward to the failing service).
   - Never configure the fallback to "allow all" — configure it to "deny all."
   ```ts
   const authzCircuitBreaker = new CircuitBreaker(authzService.check, {
     fallback: () => { throw new ForbiddenError('Authorization service unavailable'); },
   });
   ```

6. **Test exceptional conditions explicitly with fault injection.** Build tests that deliberately trigger exceptions in security code paths:
   ```ts
   it('denies access when authz service throws', async () => {
     authzService.check.mockRejectedValue(new Error('Network timeout'));
     const response = await request(app).get('/protected-resource').set('Authorization', `Bearer ${token}`);
     expect(response.status).toBe(403);  // must deny, not 200 or 500 without auth
   });
   ```
   Use chaos engineering tools (Chaos Monkey, fault injection in staging) to verify behavior under real failure conditions.

7. **Ensure financial and transactional operations are idempotent.** If a payment operation fails partway through, the system must not: charge twice on retry, apply a discount twice, create two orders. Use idempotency keys:
   ```ts
   await stripe.paymentIntents.create({
     amount: 1000,
     currency: 'usd',
     idempotencyKey: `order-${orderId}-payment`,
   });
   ```

## References
- OWASP A10:2021 – Server-Side Request Forgery (note: A10:2025 expanded to include exceptional conditions)
- OWASP Error Handling Cheat Sheet
- Release It! — Michael Nygard (circuit breakers and stability patterns)
- OWASP Application Security Verification Standard (ASVS) Section 8 — Error Handling
