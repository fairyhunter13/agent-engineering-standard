---
name: pii-minimization
description: Minimize PII exposure across analytics and event pipelines to limit compliance perimeter and breach risk.
discipline: data
tags: [data, privacy, gdpr, pii, compliance]
---

# PII Minimization

## When to use
Handling user data in analytics pipelines, data lakes, or event streams subject to GDPR, CCPA, or similar privacy regulations.
Apply this at design time for any new data store, and as a remediation audit for existing pipelines before a compliance review.

## Signal
- Full names, email addresses, or phone numbers appear in raw analytics events sent to third-party tools.
- PII fields exist in Kafka topics or S3 event logs without masking or tokenization.
- No documented data retention policy; data is kept indefinitely "just in case."
- A GDPR "right to erasure" request takes weeks to fulfill because PII is scattered across dozens of stores.
- Developers query production databases containing raw PII for debugging.
- PII is present in log lines, crash reports, or error messages.

## Why
GDPR Article 5(1)(c) mandates data minimization: collect only what is adequate, relevant, and necessary.
CCPA grants consumers the right to deletion, which is only tractable if you know where every copy of their data lives.
PII in a data pipeline broadens the compliance perimeter: every store, queue, and analytics tool that touches it becomes a regulated system.
The blast radius of a data breach is directly proportional to the volume and sensitivity of PII you hold.
Pseudonymization at the source prevents the problem from propagating — it is far cheaper than retrofitting deletion across a data lake.

## Remediate
1. **Classify before ingesting**: Build a data dictionary that labels every field as `PII`, `SENSITIVE`, `INTERNAL`, or `PUBLIC` before the first byte enters the pipeline. Unclassified data defaults to PII-treatment.
2. **Pseudonymize at ingest boundary**: Replace email addresses and names with a pseudonymous token: `HMAC-SHA256(email, rotating_secret_key)`. Store the mapping only in a secure key store. Downstream analytics work with tokens; only authorized services can reverse the mapping.
3. **Purpose limitation**: Enforce a "why are we collecting this?" review for each new field. Reject fields that serve no documented, current purpose. Analytics events should carry behavioral signals (clicked, purchased) — not identity attributes.
4. **Retention TTLs**: Set automated TTL deletion for raw PII: 90 days in event logs, 1 year in the warehouse, indefinite for aggregates only. Implement in your pipeline (Kafka topic TTL, S3 lifecycle rules, warehouse scheduled deletes).
5. **Right to erasure pipeline**: Build and test a `user_deletion_pipeline` that, given a `user_id`, deletes or anonymizes all records across every store. Run quarterly drills. Deletion must complete within 30 days (GDPR Art. 17) — automate, do not rely on manual tickets.
6. **Never log PII**: Audit log statements for email, name, SSN, card number, IP address patterns. Use structured logging with field-level redaction. Add a lint rule or secret scanner (e.g., `detect-secrets`) to CI to catch PII in logs at PR time.

## References
- GDPR Articles 5, 17, 25 (data minimization, erasure, privacy by design)
- CCPA/CPRA: consumer deletion rights
- OWASP Top 10 Privacy Risks
- NIST SP 800-188: De-identifying Government Datasets
- AWS re:Invent: "Building GDPR-compliant architectures on AWS"
