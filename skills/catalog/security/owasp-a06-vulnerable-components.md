---
name: owasp-a06-vulnerable-components
description: Patch known CVEs in libraries and runtime environments within defined SLAs using automated SCA scanning and a documented vulnerability response process.
discipline: security
tags: [owasp, dependencies, cve, patching, sca]
---

# OWASP A06: Vulnerable and Outdated Components

## When to use
Apply this skill when responding to CVE alerts, when building a dependency patch management process, when a security audit identifies outdated components, or when establishing SLA targets for vulnerability remediation.

## Signal
- A library in production has a known CVE with CVSS ≥ 7.0 that is not being tracked.
- Dependencies have not been updated in more than 90 days.
- No automated SCA (Software Composition Analysis) scanning in CI.
- Base OS images in Docker containers are using EOL versions (Ubuntu 18.04, Debian Buster).
- Language runtime is an EOL version (Node.js 16, Python 3.8, Java 8 without commercial support).
- `npm audit` / `pip-audit` / `govulncheck` finds HIGH or CRITICAL findings with available patches.
- "We'll update dependencies next quarter" is the standing answer to vulnerability alerts.

## Why
A06:2025 is the highest-impact routine vulnerability management task. Attackers actively scan for known vulnerabilities using automated tools (Shodan, Nuclei, Metasploit modules) the moment CVEs are published. The window between CVE publication and exploitation in the wild has shrunk from weeks to days in 2025. Log4Shell (CVE-2021-44228), Spring4Shell (CVE-2022-22965), and similar vulnerabilities demonstrated that widely-used libraries can be exploited at global scale within 48 hours of disclosure. Keeping dependencies patched is the highest-ROI security practice.

## Remediate

1. **Run SCA in CI on every build.** Integrate multiple tools for coverage:
   ```yaml
   # GitHub Actions — multi-tool SCA pipeline
   - name: trivy vulnerability scan
     run: trivy fs --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed .

   - name: govulncheck (Go)
     run: govulncheck ./...

   - name: npm audit
     run: npm audit --audit-level=high

   - name: pip-audit (Python)
     run: pip-audit --require-hashes -r requirements.txt
   ```
   `trivy` is the recommended primary tool — it scans OS packages, language deps, IaC, and container images in a single scan.

2. **Define and enforce a vulnerability SLA policy.** Document in your security policy and enforce via tracking:
   | CVSS Score | Severity | Patch Deadline |
   |-----------|----------|---------------|
   | 9.0 – 10.0 | Critical | 24 hours |
   | 7.0 – 8.9  | High     | 7 days   |
   | 4.0 – 6.9  | Medium   | 30 days  |
   | 0.1 – 3.9  | Low      | 90 days  |
   Track unpatched vulnerabilities in your issue tracker with due dates.

3. **Automate dependency update PRs.** Configure Dependabot (GitHub) or Renovate (any platform) to create automatic PRs for security updates and patch releases:
   ```yaml
   # .github/dependabot.yml
   updates:
     - package-ecosystem: npm
       directory: /
       schedule:
         interval: daily
       open-pull-requests-limit: 20
     - package-ecosystem: docker
       directory: /
       schedule:
         interval: weekly
   ```
   Configure auto-merge for patch-level security updates with passing CI. Require human review for minor/major updates.

4. **Patch base OS images and language runtimes.** Application-layer scanning misses OS-level vulnerabilities (OpenSSL, curl, libssl) in container base images:
   ```dockerfile
   # Always use specific, non-EOL versions
   FROM node:22-alpine3.20  # not node:latest, not node:16

   # Run OS security updates as part of the build
   RUN apk upgrade --no-cache
   ```
   Rebuild and redeploy container images weekly even with no code changes to pick up OS security patches.

5. **Scan container images in CI and in registry.** Scan container images both at build time and continuously in your registry:
   ```sh
   # Build-time scan
   trivy image --exit-code 1 --severity HIGH,CRITICAL myapp:latest

   # Registry scanning: ECR enhanced scanning, GCR Container Analysis, Docker Scout
   ```

6. **Create an inventory of all components.** You cannot patch what you do not know you have. Maintain an SBOM (see `owasp-a03-supply-chain-and-sbom.md`) and cross-reference it against the OSV database for new CVEs automatically.

7. **Handle unfixable vulnerabilities with compensating controls.** When a patched version is not yet available:
   - Apply WAF rules to block exploit patterns.
   - Disable the vulnerable feature if it is not needed.
   - Network-isolate the vulnerable component.
   - Document the risk acceptance decision with a review date.

8. **Track EOL dates for language runtimes and frameworks.** Subscribe to EOL notifications for your stack at `endoflife.date`. Set a calendar reminder 3 months before EOL to plan the upgrade. After EOL, no security patches are released — EOL runtimes must be upgraded regardless of known CVEs.

## References
- OWASP A06:2021 – Vulnerable and Outdated Components
- NVD (National Vulnerability Database) — nvd.nist.gov
- OSV.dev — Open Source Vulnerabilities database
- trivy (aquasecurity/trivy)
- Dependabot documentation (GitHub)
- endoflife.date
