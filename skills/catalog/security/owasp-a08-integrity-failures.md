---
name: owasp-a08-integrity-failures
description: Prevent CI/CD pipeline tampering, unsafe deserialization, and unsigned artifact promotion by signing builds and pinning action versions.
discipline: security
tags: [owasp, integrity, ci-cd, supply-chain, deserialization]
---

# OWASP A08: Software and Data Integrity Failures

## When to use
Apply this skill when reviewing CI/CD pipeline security, when handling deserialization of untrusted data, when establishing code signing requirements, or when ensuring that auto-update mechanisms verify signatures before applying updates.

## Signal
- GitHub Actions workflows use `uses: actions/checkout@v4` (mutable tag) instead of pinned commit hash.
- CI/CD pipeline deploys whatever is pushed to `main` without signature verification.
- `pickle.loads(user_provided_data)` or Java `ObjectInputStream` without an allowlist.
- NPM packages installed during CI without lockfile (`npm install` instead of `npm ci`).
- Build artifacts not signed — anyone who gains deploy access can push any binary.
- Auto-update mechanism fetches updates from a CDN without verifying signatures.
- OIDC not used for cloud authentication — long-lived static credentials used in CI.

## Why
A08:2025 covers a class of vulnerabilities where code or data can be modified without detection, then trusted and executed. CI/CD pipelines are high-value targets: compromising a pipeline gives attackers the ability to inject malicious code into production software at build time, reaching all users at once. The SolarWinds breach (2020) compromised the build pipeline — not the application code. Deserialization vulnerabilities allow arbitrary code execution because deserialization of attacker-controlled data can instantiate arbitrary classes and trigger their constructors/methods. Integrity verification (signatures, hashes) is the primary defense.

## Remediate

1. **Pin GitHub Actions to commit SHAs, not mutable tags.** `@v4` is a mutable reference — the action maintainer can push malicious code to the same tag. Commit SHAs are immutable:
   ```yaml
   # Bad — mutable tag
   uses: actions/checkout@v4

   # Good — pinned to immutable commit SHA
   uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
   ```
   Use Dependabot for automated SHA updates:
   ```yaml
   # .github/dependabot.yml
   - package-ecosystem: github-actions
     directory: /
     schedule:
       interval: weekly
   ```

2. **Use OIDC for cloud authentication in CI — not long-lived secrets.** OIDC tokens are short-lived (minutes) and scoped to a specific workflow run. Long-lived static credentials (AWS access keys stored as secrets) are stolen via secrets exposure:
   ```yaml
   # AWS OIDC authentication (no static secrets)
   - name: Configure AWS credentials
     uses: aws-actions/configure-aws-credentials@010d0da01d0b5a38af31e9c3470dbfdabdecca3a  # pinned
     with:
       role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
       aws-region: us-east-1
   ```
   Configure the IAM role to only trust workflows from specific GitHub repos and branches.

3. **Sign build artifacts with Sigstore/cosign.** Generate a verifiable attestation for every build artifact:
   ```sh
   # Sign a container image with cosign (keyless, using OIDC)
   cosign sign --yes myregistry.io/myapp:v1.2.3@sha256:abc123

   # Verify before deploying
   cosign verify \
     --certificate-identity-regexp "https://github.com/myorg/myapp/.github/workflows/.*" \
     --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
     myregistry.io/myapp:v1.2.3
   ```
   Add signature verification as a deploy gate — no unsigned images reach production.

4. **Use `npm ci` instead of `npm install` in CI.** `npm ci` installs exactly what is in `package-lock.json` — it does not resolve ranges or update the lockfile. This ensures reproducibility and catches lockfile tampering:
   ```yaml
   - name: Install dependencies
     run: npm ci  # never npm install in CI
   ```

5. **Avoid unsafe deserialization of untrusted data.** Never deserialize data from untrusted sources (user input, external APIs, public queues) using formats that support arbitrary object instantiation:
   ```python
   # Python — NEVER use pickle with untrusted data
   import pickle
   data = pickle.loads(user_provided_bytes)  # CRITICAL: arbitrary code execution

   # Safe alternatives for external data:
   import json
   data = json.loads(user_provided_bytes)  # safe — no code execution

   # If you must use a binary format, use MessagePack or Protocol Buffers
   # with a strict schema — not pickle or Java serialization
   ```
   For Java: never use `ObjectInputStream` with untrusted data. Use an allowlist-based filter:
   ```java
   // Java — safe deserialization with allowlist
   ObjectInputFilter filter = ObjectInputFilter.allowFilter(
     clazz -> List.of(AllowedClass1.class, AllowedClass2.class).contains(clazz),
     ObjectInputFilter.Status.REJECTED
   );
   ObjectInputStream ois = new ObjectInputStream(stream);
   ois.setObjectInputFilter(filter);
   ```

6. **Verify integrity of downloaded artifacts.** Any file downloaded during CI (binaries, installers, archives) must have its checksum verified:
   ```sh
   # Download and verify checksum
   curl -fsSL https://example.com/tool-v1.2.3-linux.tar.gz -o tool.tar.gz
   echo "expected_sha256  tool.tar.gz" | sha256sum -c
   ```

7. **Aim for SLSA Level 2+ for critical services.** SLSA (Supply-chain Levels for Software Artifacts) is a framework for build integrity:
   - Level 1: Build scripts checked in to source control.
   - Level 2: Hosted build platform (GitHub Actions, GCB) with signed provenance.
   - Level 3: Isolated builds with signed provenance (recommended for critical services).
   Use `slsa-github-generator` to generate SLSA provenance automatically.

8. **Audit pipeline permissions.** Review GitHub Actions workflow permissions:
   ```yaml
   permissions:
     contents: read    # not write, unless needed
     id-token: write   # only for OIDC
     packages: write   # only for image push step
   ```
   Use `step-security/harden-runner` to enforce least-privilege at the runner level.

## References
- OWASP A08:2021 – Software and Data Integrity Failures
- Sigstore / cosign (sigstore.dev)
- SLSA Supply-chain Levels for Software Artifacts (slsa.dev)
- OWASP Deserialization Cheat Sheet
- step-security/harden-runner (GitHub Actions security)
