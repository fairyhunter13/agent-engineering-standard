---
name: owasp-a02-security-misconfiguration
description: Harden service configurations by disabling debug mode, setting security headers, removing default credentials, and scanning IaC for misconfigurations.
discipline: security
tags: [owasp, configuration, security, hardening, headers]
---

# OWASP A02: Security Misconfiguration

## When to use
Apply this skill when deploying a new service to production, during a security audit or penetration test review, when reviewing default framework or cloud service settings, or when IaC (Terraform, CloudFormation) is being written or reviewed.

## Signal
- `DEBUG=True` or equivalent set in a production environment.
- Stack traces, SQL queries, or internal paths visible in 500 error responses.
- Default admin credentials unchanged on database, admin panels, or cloud services.
- Unused HTTP methods (PUT, DELETE, TRACE) enabled on endpoints that do not need them.
- S3 buckets, GCS buckets, or Azure Blob containers set to public access.
- `Access-Control-Allow-Origin: *` on APIs that return authenticated data.
- Cloud security scan (`checkov`, `tfsec`) finds HIGH severity findings in IaC.
- Server version disclosed in `Server: Apache/2.4.51` response header.

## Why
A02:2025 moved from #5 in OWASP 2017 to #2 in 2021 and remains there in 2025. Misconfigurations are the most common finding in penetration tests and the easiest to exploit — they require no custom exploit code, just default credentials or exposed endpoints. Misconfigured cloud storage (public S3 buckets) has been the direct cause of some of the largest data breaches in history. Unlike code vulnerabilities, misconfigurations often exist from day one and are never noticed until an audit or incident.

## Remediate

1. **Disable debug mode in production.** Debug mode in web frameworks exposes stack traces, environment variables, loaded modules, and internal configuration in error responses. Enforce this in deployment configuration:
   ```bash
   # Django
   DEBUG=False
   # Rails
   config.consider_all_requests_local = false
   # Express.js — never use this middleware in prod
   app.use(errorHandler())  # remove or replace with generic error handler
   # Spring Boot
   server.error.include-stacktrace=never
   server.error.include-message=never
   ```

2. **Sanitize error responses.** Production 500 errors must return generic messages — never stack traces, database errors, or internal paths:
   ```ts
   // Express.js global error handler
   app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
     logger.error('Unhandled error', { error: err.message, stack: err.stack, path: req.path });
     res.status(500).json({ error: 'Internal server error' }); // no details to client
   });
   ```

3. **Change all default passwords before deploying.** Audit every component: databases, admin panels (phpMyAdmin, Kibana, Grafana), message brokers (RabbitMQ, Kafka UI), CI systems (Jenkins), container registries, and cloud service default credentials. Use a secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) — not `.env` files.

4. **Remove unused features, endpoints, and HTTP methods.** Disable TRACE, CONNECT HTTP methods at the reverse proxy level. Remove unused framework plugins. Disable default admin routes (`/admin`, `/phpmyadmin`, `/actuator` without auth):
   ```nginx
   # Disable TRACE at nginx
   if ($request_method = TRACE) { return 405; }
   ```

5. **Set all standard security response headers.** Apply these on every HTTP response (via reverse proxy or application middleware):
   ```
   Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
   X-Frame-Options: DENY
   X-Content-Type-Options: nosniff
   Referrer-Policy: strict-origin-when-cross-origin
   Permissions-Policy: camera=(), microphone=(), geolocation=()
   Content-Security-Policy: default-src 'self'; ...
   ```
   Remove: `Server`, `X-Powered-By`, `X-AspNet-Version` headers (they disclose server technology).

6. **Harden cloud storage.** Enforce at the IaC level:
   ```hcl
   # Terraform — S3 bucket
   resource "aws_s3_bucket_public_access_block" "app" {
     bucket                  = aws_s3_bucket.app.id
     block_public_acls       = true
     block_public_policy     = true
     ignore_public_acls      = true
     restrict_public_buckets = true
   }
   ```
   Enable AWS S3 Block Public Access at the account level as a failsafe.

7. **Scan IaC for misconfigurations in CI.** Add infrastructure scanning to every PR:
   ```yaml
   # GitHub Actions
   - name: checkov IaC scan
     uses: bridgecrewio/checkov-action@v12
     with:
       directory: ./terraform
       framework: terraform
       soft_fail: false
       halt_on_broken_checks: HIGH
   ```
   Alternative tools: `tfsec`, `kics` (Checkmarx), `terrascan`.

8. **Harden CORS.** Allowlist specific origins for APIs that return authenticated data:
   ```ts
   const corsOptions = {
     origin: ['https://app.example.com', 'https://admin.example.com'],
     credentials: true,
   };
   app.use(cors(corsOptions));
   ```

9. **Scan headers regularly.** Use Mozilla Observatory (`https://observatory.mozilla.org`) or SecurityHeaders.com to score your security headers. Target grade A or A+.

## References
- OWASP A02:2021 – Security Misconfiguration
- Mozilla Observatory (observatory.mozilla.org)
- checkov (bridgecrewio/checkov) — IaC security scanning
- tfsec (aquasecurity/tfsec)
- OWASP Security Headers Project
