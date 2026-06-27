---
name: secrets-management
description: Store, rotate, and inject secrets (API keys, DB passwords, TLS certs) securely without hardcoding them in code or manifests.
discipline: infra
tags: [security, secrets, vault, kubernetes, devops]
---

# Secrets Management

## When to use

Secrets (API keys, database passwords, TLS certificates, OAuth tokens) appear in source code, Docker
image layers, CI logs, or Kubernetes ConfigMaps. Manual rotation of secrets causes downtime or
requires a redeploy. A security scan reveals credentials in git history. Access to secrets is not
audited — there is no record of which service or person accessed a secret and when.

## Signal

- `git log -p | grep -i 'password\|secret\|api_key'` returns matches — credentials in history.
- `docker history <image>` shows environment variables containing secrets set via `ENV` in
  Dockerfile.
- Kubernetes Secrets stored as base64 in etcd with no encryption at rest — plaintext to anyone with
  etcd access.
- CI/CD pipeline logs show `echo $SECRET` or environment dump commands that expose values.
- Rotating a DB password requires updating environment variables in every deployment manually.
- No audit log of who accessed production credentials.

## Why

Secrets in source code are exposed to every developer with repository access, every CI runner, and
anyone who clones the repo — including compromised accounts. Image layers are permanent; a secret
set via `ENV` in a Docker layer persists even after a subsequent `RUN unset` — it is visible in
`docker history`. Base64 encoding is not encryption; a Kubernetes Secret with no encryption at rest
is readable by anyone with etcd access or the right RBAC permissions.

Defense in depth requires: secrets stored encrypted, rotated automatically, injected at runtime (not
baked in), and with every access audited.

## Remediate

1. **Store secrets in a dedicated secrets manager.** Never in code, image layers, or ConfigMaps.
   - **HashiCorp Vault**: open-source, feature-rich, supports dynamic secrets (auto-generated DB
     credentials), Kubernetes auth, audit logging.
   - **AWS Secrets Manager**: managed, native AWS IAM integration, automatic rotation for RDS.
   - **GCP Secret Manager**: managed, IAM-based, version tracking.
   - **Azure Key Vault**: managed, AD integration.

2. **Inject secrets into Kubernetes pods at runtime — not at build time.**
   - **External Secrets Operator (ESO)**: syncs secrets from Vault/AWS/GCP into Kubernetes Secrets
     automatically. The ESO manifest references the secret store; the K8s Secret is created by ESO
     and rotated when the source changes.
   - **Vault Agent Sidecar Injector**: injects secrets as files into pod filesystem via a sidecar.
   - **Never use ConfigMaps for secrets** — they are not encrypted and not treated as sensitive by
     RBAC policies.

3. **Enable encryption at rest for etcd in Kubernetes.** Even Kubernetes Secrets (which are separate
   from Vault) should be encrypted:
   ```yaml
   # /etc/kubernetes/encryption-config.yaml
   kind: EncryptionConfiguration
   resources:
     - resources: [secrets]
       providers:
         - aescbc:
             keys:
               - name: key1
                 secret: <base64-encoded-32-byte-key>
         - identity: {}
   ```
   Managed K8s services (EKS, GKE, AKS) provide envelope encryption via their KMS integrations.

4. **Rotate secrets on a schedule.** Set rotation policies:
   - TLS certificates: 90 days (use cert-manager for automated rotation).
   - Database passwords: 180 days; use Vault dynamic secrets for zero-downtime rotation.
   - API keys: rotate after any suspected compromise, or annually.
   Use Vault's `lease_duration` and automatic renewal for applications that check for secret changes.

5. **Never print secrets in CI.** Audit CI pipeline definitions for: `env`, `echo $VAR`, `printenv`,
   `set -x`. Use secret masking in your CI platform (GitHub Actions, GitLab CI, etc.) — but treat
   masking as a safety net, not the primary protection.

6. **Audit secret access via Vault audit logs.** Enable the file audit backend in Vault and ship
   logs to your SIEM. Alert on: unexpected principals accessing production secrets, access outside
   business hours, high-frequency access from unexpected IPs.

7. **Scan repositories for committed secrets.** Use `git-secrets`, `trufflehog`, or `gitleaks` in
   pre-commit hooks and CI. Rotate any secrets found immediately — assume they are compromised.

## References

- HashiCorp Vault documentation
- External Secrets Operator documentation (external-secrets.io)
- cert-manager documentation (cert-manager.io)
- trufflehog / gitleaks: secret scanning tools
- Kubernetes documentation: Encrypting Secret Data at Rest
