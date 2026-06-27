---
name: dependency-hygiene
description: Keep the dependency graph minimal, licensed correctly, and free of unmaintained or vulnerable packages.
discipline: craft
tags: [dependencies, maintenance, licenses, security, npm]
---

# Dependency Hygiene

## When to use
Adding a new third-party dependency; running a dependency audit before a release or security review; reducing bundle size or transitive dep footprint.
Apply this before any `npm install <pkg>`, `go get`, `pip install`, or equivalent action, and quarterly as a standing audit.

## Signal
- `node_modules` contains 2,000+ packages for a medium-complexity application; most are transitive.
- A `devDependency` (test framework, build tool) is included in the production bundle or Docker image.
- `npm audit` or `dependabot` reports critical CVEs in a package you use directly or transitively.
- A package with a GPL or AGPL license is included in a proprietary MIT-licensed project — a license conflict.
- A critical-path dependency has not had a commit or release in 3+ years and the maintainer is unresponsive.
- `package.json` or `go.mod` contains packages that are no longer imported by any source file.

## Why
Dependencies are liabilities, not just assets.
Every dependency you add is a surface area for CVEs, a license obligation, a maintenance burden when it breaks, and a supply-chain attack vector.
The risk is non-linear: a single transitive dependency (one you did not choose) can introduce a critical vulnerability that you are responsible for patching.
License violations are a legal risk: GPL in a proprietary codebase can require you to open-source your entire application.
An unmaintained package will not receive security patches; you will either inherit the vulnerability or be forced into an unplanned migration under pressure.

## Remediate
1. **Before adding any dependency**, evaluate four criteria: (a) **Maintenance** — last release date, open issues trend, repository activity; reject if last release >2 years ago with no activity. (b) **License** — must be permissive (MIT, Apache 2.0, BSD); flag GPL/LGPL/AGPL for legal review. (c) **Popularity** — weekly download count signals community vetting; prefer packages with millions of weekly downloads for critical functionality. (d) **Transitive footprint** — run `npm why <pkg>` or `go mod graph` to see what it pulls in; reject if it adds dozens of transitive dependencies for minor functionality.
2. **Prefer the standard library** for small utilities: string manipulation, date formatting, base64 encoding, UUID generation, HTTP clients. The standard library is zero-cost, already present, and has no CVE surface or license risk.
3. **Separate dev from prod dependencies** explicitly: `devDependencies` in npm, build-tagged imports in Go. Audit that your production Docker image does not include test frameworks, code generators, or build tools.
4. **Prune unused dependencies**: run `depcheck` (npm), `pip-check` (Python), or `go mod tidy` (Go) to find declared dependencies that are no longer imported. Remove them; unused code is still a CVE and compliance surface.
5. **License check in CI**: add an automated license scan to your CI pipeline. Tools: `license-checker` (npm), `pip-licenses` (Python), `golicense` (Go). Define an allowed-license list and fail the build on any unlisted license.
6. **Keep dependencies current**: enable Dependabot or Renovate Bot for automated PR creation on patch and minor version updates. Review and merge these weekly. Falling behind on updates makes each update larger and riskier, creating a compound maintenance debt.

## References
- OWASP Top 10: A06 — Vulnerable and Outdated Components
- npm documentation: `npm audit` and `npm dedupe`
- Go documentation: `go mod tidy` and `go mod why`
- SPDX License List (spdx.org/licenses) — canonical license identifiers
- Supply chain attacks: SolarWinds, event-stream, ua-parser-js as case studies
