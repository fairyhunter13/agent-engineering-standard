---
name: shift-left-sast-dast-sca
description: Build a DevSecOps pipeline with SAST, SCA, DAST, and secret scanning at the appropriate CI/CD gates to find security defects early and cheaply.
discipline: security
tags: [security, sast, dast, sca, devSecOps, ci-cd]
---

# Shift-Left Security: SAST, DAST, SCA

## When to use
Apply this skill when building or improving a DevSecOps pipeline, when security findings are consistently discovered late (in staging or production), when a security audit recommends automated scanning, or when onboarding a new application to a secure SDLC.

## Signal
- Security vulnerabilities discovered for the first time in a manual penetration test.
- No security scanning runs in CI — the first automated check is a pre-production scan.
- Developers are unaware of common vulnerability patterns (SQL injection, XSS, path traversal) in the languages they use.
- `npm audit` or `pip-audit` is run manually at best, never in CI.
- No secret scanning in CI — secrets discovered only after a production incident.
- Security team is a bottleneck: every deployment requires a manual security review.

## Why
Security defects found at different SDLC stages have dramatically different remediation costs. NIST estimates: design = $1, code = $6, unit test = $16, integration test = $33, system test = $68, production = $150 (relative cost). Shift-left security applies automated scanning at the earliest appropriate stage — static code analysis (SAST) at commit/PR time, dependency scanning (SCA) at build time, dynamic analysis (DAST) at staging — to catch defects when they are cheapest to fix. Additionally, automated scanning scales with team size; manual security review does not.

## Remediate

### Layer 1: Pre-commit (developer workstation)

1. **Secret scanning pre-commit hook.** The lowest-cost, highest-value pre-commit gate:
   ```yaml
   # .pre-commit-config.yaml
   repos:
     - repo: https://github.com/gitleaks/gitleaks
       rev: v8.18.0
       hooks:
         - id: gitleaks
     - repo: https://github.com/Yelp/detect-secrets
       rev: v1.4.0
       hooks:
         - id: detect-secrets
   ```
   Install across the team via `pre-commit install` in the project README onboarding steps.

### Layer 2: PR / CI (every pull request)

2. **SAST — static application security testing.** Scan source code for vulnerability patterns on every PR:
   ```yaml
   # GitHub Actions — Semgrep SAST
   - name: Semgrep SAST
     uses: returntocorp/semgrep-action@v1
     with:
       config: >-
         p/python
         p/javascript
         p/typescript
         p/sql-injection
         p/xss
         p/secrets
       auditOn: push
   ```
   Alternative tools:
   - **Sonarqube** (self-hosted): comprehensive, supports 30+ languages, quality gates.
   - **CodeQL** (GitHub-native): deep semantic analysis, free for public repos.
   - **Bandit** (Python-only): fast, no config needed.
   - **ESLint security plugins** (`eslint-plugin-security`, `eslint-plugin-no-unsanitized`) for JS/TS.

3. **SCA — software composition analysis.** Scan dependencies for known CVEs on every build:
   ```yaml
   # GitHub Actions — trivy dependency scan
   - name: Trivy SCA scan
     uses: aquasecurity/trivy-action@master
     with:
       scan-type: fs
       severity: HIGH,CRITICAL
       exit-code: 1
       ignore-unfixed: true
   ```
   Also enable Dependabot security alerts (GitHub) or Snyk (cross-platform) for continuous monitoring between builds.

4. **Secret scanning in CI.** Safety net for any secret that bypassed the pre-commit hook:
   ```yaml
   - name: Trufflehog secret scan
     uses: trufflesecurity/trufflehog@main
     with:
       path: ./
       only-verified: true
   ```

5. **Fail PRs on HIGH/CRITICAL findings.** Security scanning must be a required PR gate with clear policy:
   ```yaml
   # Branch protection rule (GitHub Settings → Branches)
   # Required status checks:
   # ✓ Semgrep / semgrep
   # ✓ Trivy / trivy-fs-scan
   # ✓ Gitleaks / detect-secrets
   ```
   Exceptions to HIGH/CRITICAL findings require: security engineer approval, a risk acceptance comment on the PR, and a follow-up ticket with a remediation deadline.

### Layer 3: Staging / pre-release (DAST)

6. **DAST — dynamic application security testing.** Run against a deployed staging environment (not just source code):
   ```yaml
   # GitHub Actions — OWASP ZAP baseline scan
   - name: ZAP Baseline Scan
     uses: zaproxy/action-baseline@v0.9.0
     with:
       target: 'https://staging.example.com'
       rules_file_name: '.zap/rules.tsv'
       cmd_options: '-a -j'   # Ajax spider, JSON report
   ```
   DAST catches: authentication bypasses, XSS in rendered pages, security header misconfigurations, open redirect, SSRF — things that SAST cannot detect without running the application.

   Alternative: **Nuclei** (ProjectDiscovery) — template-based scanner with thousands of vulnerability templates, fast and customizable:
   ```sh
   nuclei -u https://staging.example.com -t nuclei-templates/ -severity high,critical
   ```

7. **Infrastructure scanning.** Scan IaC (Terraform, CloudFormation, Kubernetes manifests) in CI:
   ```yaml
   - name: Checkov IaC scan
     uses: bridgecrewio/checkov-action@v12
     with:
       directory: ./terraform
       soft_fail: false
   - name: kubesec scan
     run: kubesec scan k8s/deployment.yaml
   ```

### Layer 4: Continuous / periodic

8. **Nightly comprehensive scans.** Run slower, more comprehensive scans on schedule:
   ```yaml
   # .github/workflows/security-nightly.yml
   on:
     schedule:
       - cron: '0 2 * * *'  # 2am nightly
   jobs:
     full-dast:
       runs-on: ubuntu-latest
       steps:
         - name: Full ZAP active scan
           uses: zaproxy/action-full-scan@v0.7.0
           with:
             target: 'https://staging.example.com'
   ```

9. **Build a security champion program.** Automated tools catch known patterns; security champions (engineers trained in secure coding) catch novel patterns in code review. Train 1 security champion per 5–10 engineers. Give them access to security tooling dashboards and include them in PR reviews for security-sensitive code.

## References
- OWASP DevSecOps Guideline
- Semgrep (semgrep.dev) — SAST
- OWASP ZAP (zaproxy.org) — DAST
- Trivy (aquasecurity/trivy) — SCA + container scanning
- Nuclei (projectdiscovery/nuclei) — DAST templates
- Checkov (bridgecrewio/checkov) — IaC scanning
- NIST — "The Economic Impacts of Inadequate Infrastructure for Software Testing" (2002)
