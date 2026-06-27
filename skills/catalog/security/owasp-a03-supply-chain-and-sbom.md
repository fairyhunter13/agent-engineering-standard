---
name: owasp-a03-supply-chain-and-sbom
description: Secure the software supply chain by generating SBOMs, scanning dependencies for CVEs in CI, pinning versions, and vetting new packages before adoption.
discipline: security
tags: [owasp, supply-chain, sbom, sca, dependencies]
---

# OWASP A03: Supply Chain and SBOM

## When to use
Apply this skill when managing third-party dependencies, when a new CVE is disclosed affecting a library you use, when compliance (FedRAMP, SOC 2, EU Cyber Resilience Act) requires an SBOM, when `npm audit` / `pip-audit` reports HIGH severity findings, or when adding a new library to a project.

## Signal
- Dependency version ranges pinned loosely (`^1.2.0`) rather than exact versions.
- No automated CVE scanning — vulnerabilities discovered manually or through news.
- `npm audit` or `pip-audit` reports CRITICAL or HIGH severity vulnerabilities with no remediation plan.
- No SBOM generated for release artifacts.
- Unmaintained packages (last commit > 2 years, open critical issues, no maintainer response).
- Transitive dependency count not tracked — `node_modules` pulled in 800+ packages for a small app.

## Why
A03:2025 is new and reflects the explosive growth of supply chain attacks since 2020 (SolarWinds, Log4Shell, XZ Utils, Polyfill.io). Supply chain attacks are the fastest-growing attack vector: attackers compromise a widely-used library and reach thousands of downstream applications simultaneously. A single compromised package in a deeply-nested transitive dependency tree can execute arbitrary code during build or runtime. The EU Cyber Resilience Act (CRA, expected 2026) mandates SBOM for software sold in the EU.

## Remediate

1. **Generate an SBOM on every release artifact.** An SBOM (Software Bill of Materials) lists every component, version, and license. Generate in CycloneDX or SPDX format:
   ```sh
   # syft — universal SBOM generator
   syft packages . -o cyclonedx-json > sbom.cyclonedx.json

   # trivy — combined vulnerability scan + SBOM
   trivy sbom --format cyclonedx --output sbom.json .
   ```
   Attach the SBOM to each release on GitHub/GitLab. This is the foundation for vulnerability disclosure responses.

2. **Scan dependencies in CI on every build.** Fail the build on CRITICAL or HIGH severity findings with no fix available:
   ```yaml
   # GitHub Actions
   - name: Dependency scan
     run: |
       npm audit --audit-level=high  # fail on HIGH+
       # or
       npx snyk test --severity-threshold=high
       # or
       trivy fs --exit-code 1 --severity HIGH,CRITICAL .
   ```
   Recommended toolchain: `trivy` (polyglot, fast) + `Snyk` (better fix suggestions) + language-native tools (`npm audit`, `pip-audit`, `govulncheck`, `cargo audit`).

3. **Pin exact versions in lockfiles and commit lockfiles.** Loose version ranges (`^1.2.0`) allow a malicious version to be automatically pulled in on `npm install`. Always commit `package-lock.json`, `yarn.lock`, `poetry.lock`, `go.sum`, `Gemfile.lock`:
   ```sh
   # Use --save-exact for npm
   npm install --save-exact stripe

   # pip — pin in requirements.txt
   stripe==7.10.0
   ```
   In Docker: pin image digests, not just tags — `FROM node:20@sha256:abc123...`.

4. **Automate dependency updates with Dependabot or Renovate.** Manual dependency updates are neglected. Automate PRs for dependency bumps:
   ```yaml
   # .github/dependabot.yml
   updates:
     - package-ecosystem: npm
       directory: /
       schedule:
         interval: daily
       auto-merge: true  # auto-merge patch updates only
       versioning-strategy: lockfile-only
   ```
   Configure auto-merge for patch updates (low risk); require human review for major updates.

5. **Vet new dependencies before adoption.** Before adding any new library, evaluate:
   - **Maintenance**: last commit date, open issues, maintainer activity, number of maintainers.
   - **Popularity**: weekly downloads, GitHub stars (proxy for community vetting).
   - **License**: check for GPL/AGPL compatibility with your license.
   - **Transitive dependencies**: `npm ls --depth=3` to see the full tree — avoid packages that pull in hundreds of transitive deps.
   - **Security history**: check OSV.dev or Snyk advisor for past vulnerabilities.
   Use a package vetting checklist as part of your PR template.

6. **Monitor for new CVEs in your dependency tree.** Set up alerts:
   - GitHub Dependabot security alerts (automatic for public repos, opt-in for private).
   - `osv-scanner` (Google OpenSourceVulnerabilities) — scans lockfiles against the OSV database.
   - Snyk webhook or Slack integration for new vulnerability notifications.

7. **Respond to CVEs with a defined SLA.** Document and enforce:
   - CVSS ≥ 9.0 (Critical): patch within 24 hours.
   - CVSS ≥ 7.0 (High): patch within 7 days.
   - CVSS ≥ 4.0 (Medium): patch within 30 days.
   If no patch is available, apply a compensating control (WAF rule, feature flag, network isolation) and document it.

8. **Prefer fewer, well-maintained dependencies.** The best defense against supply chain attacks is a lean dependency tree. For each new dependency, ask: "Can we implement this in < 50 lines ourselves, or does it require significant specialized knowledge?" If the former, prefer owning the code.

## References
- OWASP A03:2021 – Injection (renamed A03:2025 to include Supply Chain)
- EU Cyber Resilience Act (CRA)
- CISA SBOM guidance (cisa.gov/sbom)
- syft (anchore/syft) — SBOM generation
- trivy (aquasecurity/trivy) — comprehensive vulnerability scanner
- OSV.dev — Open Source Vulnerability database
