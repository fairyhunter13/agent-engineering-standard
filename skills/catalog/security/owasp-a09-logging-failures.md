---
name: owasp-a09-logging-failures
description: Instrument security-relevant events with structured logs, ship to a SIEM, and alert on attack patterns to reduce mean time to detection.
discipline: security
tags: [owasp, logging, monitoring, detection, siem]
---

# OWASP A09: Security Logging and Monitoring Failures

## When to use
Apply this skill when reviewing security logging coverage, when setting up SIEM integration, when an incident postmortem reveals that attacks were not detected, or when building a new service that processes sensitive data or financial transactions.

## Signal
- Failed login attempts are not logged — no way to detect credential stuffing.
- No alerting on repeated 403/401 responses from a single IP.
- Audit trail is missing for sensitive operations (payment, role change, admin action, data export).
- Logs contain passwords, session tokens, or PII (email addresses, credit card numbers).
- Logs are written only to local disk — lost when the container/VM is replaced.
- Mean Time to Detection (MTTD) for security incidents exceeds 7 days (industry median is 197 days; target < 1 day).
- Security team cannot answer "who accessed this record on this date?" for a given user account.

## Why
A09:2025 — without comprehensive security logging, attackers operate undetected for weeks or months. The Verizon DBIR (2025) reports that the median time from attacker entry to detection is 127 days. Most of those 127 days are spent in environments with insufficient logging. Security logging is not just about detecting attacks — it is also about: forensic investigation after an incident (what data was accessed?), compliance (GDPR Article 30 requires records of processing activities, SOC 2 requires audit logs), and demonstrating compliance during audits.

## Remediate

1. **Define what MUST be logged for security purposes.** Log all of the following:
   - **Authentication events**: login success, login failure, logout, MFA success, MFA failure.
   - **Authorization events**: access denied (403), unauthorized endpoint access (401).
   - **Account management**: password change, email change, role/permission change, account creation/deletion.
   - **Sensitive data access**: reading a record containing PII, financial data, or health data.
   - **Financial/transaction events**: payment initiation, payment success/failure, refund, coupon redemption.
   - **Admin actions**: any action by an admin account, configuration change, system setting change.
   - **Security events**: lockout triggered, suspicious pattern detected, rate limit exceeded.

2. **Use structured logging with a consistent schema.** Every security-relevant event should be a structured JSON object:
   ```ts
   logger.info({
     event: 'auth.login.failed',
     userId: null,            // unknown at this point
     email: hashPII(email),   // hashed, not raw
     ipAddress: req.ip,
     userAgent: req.headers['user-agent'],
     reason: 'invalid_password',
     timestamp: new Date().toISOString(),
     requestId: req.id,
   });
   ```
   Fields: `event` (machine-readable event type), `userId`, `ipAddress`, `action`, `resource`, `resourceId`, `outcome`, `timestamp`, `requestId`.

3. **Never log sensitive data.** Establish a "never log" list:
   - Passwords (in any form).
   - Session tokens, API keys, JWTs.
   - Full credit card numbers (log only last 4 digits).
   - Full SSN / national IDs (log a hash or partial).
   - Raw email addresses in high-volume access logs (hash with a stable salt for correlation).
   - Secret encryption keys.
   Run `semgrep` rules to detect logging of sensitive fields in CI.

4. **Ship logs to a centralized SIEM with guaranteed delivery.** Local logs are lost when containers are replaced. Ship to:
   - **Datadog Logs** (SaaS, easiest for small teams).
   - **Elastic Stack** (self-hosted, powerful).
   - **Splunk** (enterprise standard).
   - **AWS CloudWatch + OpenSearch** (AWS-native).
   Use a reliable shipping agent (Fluent Bit, Filebeat, Vector) — not just `console.log`. Set minimum retention to 1 year (required by many compliance frameworks: SOC 2, PCI DSS, HIPAA).

5. **Alert on attack patterns.** Configure the following detection rules in your SIEM:
   - **Credential stuffing**: > 10 failed logins per IP in 60 seconds.
   - **Account lockout spike**: > 5 accounts locked out in 5 minutes.
   - **Privilege escalation**: any `role_change` event where destination role is `admin`.
   - **Data exfiltration signal**: > 1000 PII records read by a single user in 1 hour.
   - **Admin action outside business hours**: any admin action between 00:00–06:00 local business timezone.
   - **403 spike**: 403 response rate increases 10x above baseline (IDOR probing).

6. **Protect log integrity.** Logs are forensic evidence. Ensure:
   - Logs are append-only — application accounts should not have delete permissions on log storage.
   - Log storage is separate from application infrastructure.
   - For high compliance: write logs to a WORM (Write Once Read Many) storage tier.
   - Alert if log delivery stops — absence of logs is itself a signal.

7. **Include correlation IDs in every log.** Add a unique request/trace ID to every incoming request and propagate it through all downstream calls and all log entries for that request. This enables reconstructing the full timeline of an incident across services:
   ```ts
   app.use((req, res, next) => {
     req.id = req.headers['x-request-id'] ?? crypto.randomUUID();
     res.setHeader('x-request-id', req.id);
     next();
   });
   ```

8. **Run quarterly log audits.** Periodically ask: "Given last month's logs, can we answer:
   - Who accessed this user account on this date?
   - What records did user X read between 09:00 and 10:00?
   - When did admin Y change role for user Z?
   - Were there any failed payment attempts that were not investigated?"
   If any of these cannot be answered, the logging is insufficient.

## References
- OWASP A09:2021 – Security Logging and Monitoring Failures
- OWASP Logging Cheat Sheet
- Verizon DBIR (Data Breach Investigations Report) 2025
- Fluent Bit (fluent-bit.io) — log shipping agent
- NIST SP 800-92 — Guide to Computer Security Log Management
