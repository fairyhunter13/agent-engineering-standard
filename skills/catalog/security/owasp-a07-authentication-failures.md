---
name: owasp-a07-authentication-failures
description: Harden authentication with rate limiting, MFA, battle-tested auth libraries, secure JWT handling, and session best practices.
discipline: security
tags: [owasp, authentication, mfa, password, jwt]
---

# OWASP A07: Authentication Failures

## When to use
Apply this skill when implementing login/signup flows, when reviewing authentication security, after a security incident involving credential stuffing or account takeover, or when adding MFA to an existing application.

## Signal
- No rate limiting on login endpoint — 10,000 login attempts per minute possible.
- No account lockout or CAPTCHA after repeated failed logins.
- MFA is not available or not required for sensitive accounts (admin, finance).
- JWT validated only for structure but not signature (accepts `alg: none`).
- Session tokens passed in URL query parameters (`?session_id=abc123`).
- Password reset links do not expire (valid indefinitely).
- Session ID is not regenerated after login (session fixation vulnerability).
- "Remember me" tokens stored in localStorage (accessible to XSS).

## Why
A07:2025 — authentication failures are the primary enabler of account takeover. Credential stuffing (using leaked username/password pairs from breached sites) is the most common automated attack against login endpoints and succeeds against sites without rate limiting or MFA. In 2025, billions of credential pairs are available to attackers via data breach marketplaces. JWTs with incorrect validation (accepting `alg: none`) have caused multiple high-profile authentication bypasses. Session fixation and session token exposure are textbook vulnerabilities that remain common in custom auth implementations.

## Remediate

1. **Rate-limit login attempts.** Apply limits at two dimensions: per IP (prevents distributed attacks from one IP) and per username (prevents attacks from distributed IPs):
   ```ts
   // Express.js — express-rate-limit
   const loginLimiter = rateLimit({
     windowMs: 15 * 60 * 1000,  // 15 minutes
     max: 10,                    // 10 attempts per window per IP
     message: { error: 'Too many login attempts. Try again in 15 minutes.' },
   });
   app.post('/auth/login', loginLimiter, loginHandler);
   ```
   Additionally: lock account for 30 minutes after 5 consecutive failures on the same username (with unlock via email).

2. **Implement MFA for sensitive accounts.** At minimum, require MFA for admin users, finance users, and any account with elevated privilege:
   - **TOTP** (Time-Based One-Time Password): Google Authenticator, Authy, Microsoft Authenticator. Use `otplib` (Node.js) or `pyotp` (Python).
   - **WebAuthn/Passkeys**: phishing-resistant, uses device biometrics or hardware keys. Recommended for June 2026+ new implementations.
   - **SMS OTP**: acceptable but lowest security (SIM swapping attacks). Avoid for highest-privilege accounts.
   Use battle-tested libraries — never implement TOTP from scratch.

3. **Use established auth platforms for complex requirements.** Rolling custom authentication is a minefield:
   - **Managed**: Auth0, Clerk, Cognito (AWS), Firebase Auth.
   - **Self-hosted**: Keycloak, Ory Kratos, Authentik.
   - **OAuth2/OIDC**: if acting as a consumer of social login, use `passport.js` (Node) or `python-social-auth`.
   Custom auth is justified only for highly specific requirements that these platforms cannot serve.

4. **Validate JWTs correctly.** Every JWT validation must:
   - Verify the signature using the expected algorithm (RS256 or ES256).
   - Reject tokens with `alg: none` — never allow algorithm confusion attacks.
   - Verify `exp` (expiration) and `iss` (issuer) and `aud` (audience).
   - Never decode the payload without validating the signature first.
   ```ts
   // Node.js — jose library
   import { jwtVerify, createRemoteJWKSet } from 'jose';
   const JWKS = createRemoteJWKSet(new URL('https://auth.example.com/.well-known/jwks.json'));

   const { payload } = await jwtVerify(token, JWKS, {
     issuer: 'https://auth.example.com',
     audience: 'api.example.com',
     algorithms: ['RS256'],  // explicitly specify; never allow 'none'
   });
   ```

5. **Configure sessions securely.** HTTP cookies for session tokens must have:
   ```http
   Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=900
   ```
   - `HttpOnly`: prevents JavaScript (XSS) access.
   - `Secure`: only sent over HTTPS.
   - `SameSite=Strict`: prevents CSRF.
   - `Max-Age=900`: 15-minute idle timeout for sensitive applications.
   Regenerate the session ID immediately after login (`req.session.regenerate()`) to prevent session fixation.

6. **Never put tokens in URLs.** Session tokens, API keys, password reset tokens, and JWT tokens in URL query parameters are logged in: server access logs, browser history, Referer headers to third parties, CDN logs. Always transmit tokens in: `Authorization` headers, `HttpOnly` cookies, or POST bodies.

7. **Set appropriate token lifetimes.** Design token expiry deliberately:
   - Access token: 15 minutes (short, reduces blast radius of theft).
   - Refresh token: 7–30 days, stored in HttpOnly cookie.
   - Password reset tokens: 15–60 minutes, single-use.
   - Email verification tokens: 24 hours.
   Implement refresh token rotation: every use of a refresh token issues a new one and invalidates the old.

8. **Detect and alert on suspicious authentication patterns.** Alert on: login from a new country/device after a long absence, velocity of login attempts, password reset requests for accounts that rarely log in. These signals enable early account compromise detection.

## References
- OWASP A07:2021 – Identification and Authentication Failures
- OWASP Authentication Cheat Sheet
- OWASP JWT Security Cheat Sheet
- WebAuthn Level 2 specification (W3C)
- NIST SP 800-63B – Digital Identity Guidelines (Authentication)
