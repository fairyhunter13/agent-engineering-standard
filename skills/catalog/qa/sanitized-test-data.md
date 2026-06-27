---
name: sanitized-test-data
description: Replace real PII in test environments with synthetic or anonymized data to satisfy GDPR, HIPAA, and data minimization requirements.
discipline: qa
tags: [testing, data, privacy, gdpr, pii]
---

# Sanitized Test Data

## When to use
Apply this skill when any test environment (dev, staging, CI) contains real user data copied from production; when a GDPR or HIPAA audit is pending; when a developer can query the staging DB and see real names, emails, phone numbers, or financial data; or when building a data pipeline for generating test fixtures.

## Signal
- `pg_dump prod_db | psql staging_db` is the documented process for refreshing staging.
- Developers can run `SELECT email FROM users LIMIT 10` on staging and see real email addresses.
- Test fixtures contain strings like `john.doe@company.com`, `SSN: 123-45-6789`, or real credit card numbers.
- GDPR audit identifies test environments as storing personal data without a legal basis.
- Security incident disclosures have occurred from test environment compromises.
- No data masking step exists in the database refresh pipeline.

## Why
Real PII in test environments violates GDPR Article 5(1)(e) (storage limitation) and Article 25 (data protection by design). Under GDPR, test environments have a much weaker legal basis for holding personal data than production. HIPAA similarly prohibits using real PHI in non-production environments without explicit authorization. Beyond compliance, test environments are generally less secure than production — weaker access controls, more developers with DB access, less monitoring. A breach of staging data exposes real users.

## Remediate

1. **Establish a policy: no PII in non-production environments.** This policy must be documented, communicated to all engineers, and enforced technically (not just procedurally). Define PII for your domain: names, emails, phone numbers, addresses, dates of birth, government IDs, payment card data, health data, precise location.

2. **Generate synthetic data as the default.** Use a Faker library appropriate to your stack:
   ```python
   from faker import Faker
   fake = Faker()
   user = {
     'name': fake.name(),                    # "Patricia Torres"
     'email': fake.email(),                  # "example@example.net"
     'phone': fake.phone_number(),           # "+1-555-555-5555"
     'address': fake.address(),
     'ssn': fake.ssn(),                      # structurally valid, not real
   }
   ```
   Faker libraries exist for Python, JavaScript (Faker.js), Java (JavaFaker), Go, Ruby, PHP, and more.

3. **Use statistically-preserving synthesis for large datasets.** When you need test data that reflects the distribution and relationships of your production data (for performance testing, analytics, or ML pipelines), use **Synthetic Data Vault (SDV)**:
   ```python
   from sdv.single_table import GaussianCopulaSynthesizer
   synthesizer = GaussianCopulaSynthesizer(metadata)
   synthesizer.fit(real_data)  # fit on real data
   synthetic = synthesizer.sample(num_rows=10000)  # generate synthetic rows
   ```
   SDV preserves statistical properties (distributions, correlations, referential integrity) without copying real values.

4. **If anonymizing real data: use irreversible pseudonymization.** When you must start from real data structure (for FK integrity or referential consistency), anonymize each field irreversibly:
   ```python
   def anonymize_user(row):
       return {
           'id': row['id'],  # keep PK for FK integrity
           'email': hashlib.sha256(
               (row['email'] + ANONYMIZATION_SALT).encode()
           ).hexdigest()[:20] + '@test.example.com',
           'name': fake.name(),
           'dob': generalize_to_year_range(row['dob']),  # 1980–1985 not exact date
           'phone': fake.phone_number(),
       }
   ```
   The salt must be kept secret — without it, hash reversal requires a rainbow table attack.

5. **Verify: scan the anonymized DB for surviving PII.** After anonymization, run an automated PII detection scan:
   - Presidio (Microsoft) — NER-based PII detector for text fields.
   - `scrubadub` (Python) — scrubs PII from text.
   - Regular expressions for structured PII (email `[^@]+@[^@]+\.[^@]+`, SSN `\d{3}-\d{2}-\d{4}`, CC `\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}`).
   Fail the anonymization pipeline if any PII pattern survives.

6. **Apply masking in the backup pipeline.** Data masking should occur as a pipeline step before any dump or snapshot leaves the production environment:
   ```
   Production DB → [Export] → [Mask/Anonymize] → [Import] → Staging DB
                               ↑
                  Must happen BEFORE the data crosses the trust boundary
   ```
   Never transfer an unmasked snapshot to staging and then anonymize — the transfer itself is a data breach.

7. **Document test data sources in onboarding.** New developers should never think "I'll just grab a prod snapshot." Document how to seed a local DB: `make seed-test-data` running a Faker-based seeder script.

## References
- GDPR Article 5(1)(e), Article 25 (data protection by design)
- HIPAA Safe Harbor de-identification standard
- Faker (Python) / Faker.js documentation
- Synthetic Data Vault (sdv.dev)
- Microsoft Presidio (microsoft/presidio)
