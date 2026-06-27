---
name: csp-and-frontend-security
description: Harden frontend security posture with Content Security Policy, XSS prevention, and secure HTTP response headers.
discipline: frontend
tags: [security, csp, xss, cors, headers]
---

# CSP and Frontend Security

## When to use
Apply this skill when adding Content Security Policy headers to a web app, when reviewing a frontend for XSS vulnerabilities, when CORS is configured too permissively, or when a security audit flags missing HTTP security headers.

## Signal
- `Content-Security-Policy` header absent from HTTP responses.
- `eval()` or `new Function(string)` present in source code.
- Inline `<script>` blocks without nonces or hashes.
- `dangerouslySetInnerHTML` used with any data that originates from user input or a third-party API.
- `Access-Control-Allow-Origin: *` set on endpoints that accept credentials.
- No `X-Frame-Options`, `X-Content-Type-Options`, or `Referrer-Policy` headers.
- Third-party scripts loaded via `<script src>` without Subresource Integrity (SRI) hashes.

## Why
XSS (Cross-Site Scripting) ranks in OWASP's top 5 in 2025 and is the most common frontend vulnerability. A successful XSS attack allows an attacker to execute arbitrary JavaScript in victims' browsers — stealing sessions, exfiltrating data, performing actions on behalf of users, or redirecting to phishing pages. CSP is the primary runtime defense against XSS; even if an attacker injects a `<script>` tag, CSP prevents it from executing or phoning home.

## Remediate

1. **Start with a strict CSP.** The minimum viable strict CSP for a React/Next.js app:
   ```
   Content-Security-Policy:
     default-src 'self';
     script-src 'self' 'nonce-{RANDOM_NONCE}';
     style-src 'self' 'unsafe-inline';
     img-src 'self' data: https:;
     font-src 'self';
     connect-src 'self' https://api.example.com;
     frame-ancestors 'none';
     object-src 'none';
     base-uri 'self';
   ```
   Generate a fresh cryptographic nonce per request and inject it into all inline `<script>` tags via your framework (Next.js middleware, Express nonce middleware).

2. **Use nonces for inline scripts; avoid `'unsafe-inline'`.** `'unsafe-inline'` permits all inline scripts and negates the XSS protection of CSP. Instead, inject a per-request nonce:
   ```tsx
   // Next.js middleware — generate nonce
   const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
   // Pass to Next.js via headers and use in <Script nonce={nonce}>
   ```

3. **Never pass user input to `dangerouslySetInnerHTML`.** If you must render HTML (rich text content), sanitize with DOMPurify first:
   ```ts
   import DOMPurify from 'dompurify';
   const clean = DOMPurify.sanitize(userHtml, { ALLOWED_TAGS: ['p', 'b', 'i', 'a'] });
   <div dangerouslySetInnerHTML={{ __html: clean }} />
   ```
   Prefer rendering structured data (JSON) and mapping it to React components instead of rendering raw HTML.

4. **Set all standard security headers.** In Next.js `next.config.js`:
   ```js
   headers: async () => [{
     source: '/(.*)',
     headers: [
       { key: 'X-Frame-Options', value: 'DENY' },
       { key: 'X-Content-Type-Options', value: 'nosniff' },
       { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
       { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
       { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
     ],
   }]
   ```

5. **Lock down CORS.** For endpoints that return user-specific data:
   ```ts
   // Bad
   res.setHeader('Access-Control-Allow-Origin', '*');
   // Good
   const allowed = ['https://app.example.com', 'https://admin.example.com'];
   if (allowed.includes(req.headers.origin)) {
     res.setHeader('Access-Control-Allow-Origin', req.headers.origin);
     res.setHeader('Vary', 'Origin');
   }
   ```
   Never use `*` for requests that include credentials (`withCredentials: true` / `credentials: 'include'`).

6. **Use Subresource Integrity (SRI) for third-party scripts.** When loading scripts from external CDNs, add `integrity` and `crossorigin` attributes:
   ```html
   <script
     src="https://cdn.example.com/lib.js"
     integrity="sha384-abc123..."
     crossorigin="anonymous">
   </script>
   ```
   Generate hashes with `openssl dgst -sha384 -binary lib.js | openssl base64 -A`.

7. **Deploy CSP in report-only mode first.** To avoid breaking production when deploying CSP for the first time, use `Content-Security-Policy-Report-Only` with a `report-uri`:
   ```
   Content-Security-Policy-Report-Only: default-src 'self'; report-uri /csp-report
   ```
   Monitor violations for 1–2 weeks, fix them, then switch to enforcement mode.

8. **Scan for XSS vulnerabilities.** Add `semgrep` rules (`r/javascript.react.security.audit.react-dangerously-set-innerhtml`) to CI. Run OWASP ZAP AJAX Spider against staging environments nightly.

## References
- OWASP XSS Prevention Cheat Sheet
- Content Security Policy Level 3 (W3C)
- Mozilla Observatory (observatory.mozilla.org) — header scanner
- DOMPurify (cure53/DOMPurify)
- Next.js CSP documentation
