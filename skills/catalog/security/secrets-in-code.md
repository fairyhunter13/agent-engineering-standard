---
name: secrets-in-code
description: Prevent secrets from entering the codebase with pre-commit hooks and CI scanning, and respond rapidly to leaked credentials with rotation and Git history purge.
discipline: security
tags: [security, secrets, git, credentials, scanning]
---

# Secrets in Code

## When to use
Apply this skill when preventing secrets from entering the codebase (proactive), when responding to a detected or suspected secret leak (reactive), when reviewing a new repository for historical secret exposure, or when building a secrets management process for a new team.

## Signal
- `AKIA...` (AWS access key), `sk_live_...` (Stripe live key), or `ghp_...` (GitHub token) found via `git log --all -p` or `trufflehog` scan.
- `.env` file committed to the repository (even if later deleted — it persists in Git history).
- `API_KEY = "abc123"` or `password = "hunter2"` in source files.
- `gitleaks` or `trufflehog` CI scan finds HIGH severity secret findings.
- Docker image contains secrets in environment variables committed during build (visible via `docker history`).
- Cloud provider alerts on access key usage from an unusual IP after a repository becomes public.

## Why
A secret committed to Git is effectively leaked permanently. Git history is immutable — `git rm` does not remove the file from history; it only removes it from the working tree. Bots (GitGuardian, automated scanners) monitor public GitHub repositories in real time and will detect and attempt to use leaked secrets within minutes of a push. Even private repositories are at risk when team members clone the repository to their laptops or when the repository is briefly made public by accident. The consequences range from unauthorized API charges (leaked Stripe keys) to full cloud account compromise (leaked AWS root keys).

## Remediate

### Immediate response to a detected leak

1. **Rotate the leaked credential immediately.** Before doing anything else, revoke and rotate the exposed secret. The time between detection and rotation is the window of maximum risk:
   - AWS IAM: deactivate the access key in IAM console → create a new key → update all references.
   - GitHub token: Settings → Developer settings → Personal access tokens → Revoke.
   - Stripe key: Dashboard → Developers → API keys → Roll key.
   - Database password: change password in DB, update all application configs.
   Assume the key has already been used by an attacker — investigate CloudTrail/API logs.

2. **Purge the secret from Git history using `git filter-repo`.** Do not use `git filter-branch` (deprecated, error-prone):
   ```sh
   # Install git-filter-repo
   pip install git-filter-repo

   # Remove a specific file from all history
   git filter-repo --path .env --invert-paths

   # Remove secrets from all files matching a pattern
   git filter-repo --replace-text <(echo 'LITERAL_SECRET_VALUE==>***REMOVED***')

   # Force-push all branches (coordinate with team — this rewrites history)
   git push origin --force --all
   git push origin --force --tags
   ```
   Notify all team members to re-clone or rebase — their local copies still have the secret.

3. **Report to affected services.** If the secret was for a third-party service (AWS, GitHub, Stripe), notify their security team — most have a `security@` contact. GitHub has automated secret scanning that may have already been notified.

### Prevention (proactive)

4. **Install a pre-commit hook with `gitleaks`.** Pre-commit hooks prevent secrets from being committed in the first place:
   ```yaml
   # .pre-commit-config.yaml
   repos:
     - repo: https://github.com/gitleaks/gitleaks
       rev: v8.18.0
       hooks:
         - id: gitleaks
   ```
   ```sh
   pip install pre-commit
   pre-commit install  # install hook for this repo
   pre-commit install --hook-type pre-push  # also check on push
   ```
   Alternatively, `git-secrets` (AWS Labs) or `detect-secrets` (Yelp).

5. **Run secret scanning in CI on every PR.** Pre-commit hooks can be bypassed (`--no-verify`). CI scanning provides a safety net:
   ```yaml
   # GitHub Actions
   - name: Secret scan with gitleaks
     uses: gitleaks/gitleaks-action@v2
     env:
       GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```
   Enable **GitHub Advanced Security secret scanning** for GitHub repositories — it scans all pushes automatically and alerts you when known secret patterns are detected.

6. **Maintain a strict `.gitignore`.** Block the most common secret-containing files at the repository level:
   ```gitignore
   # .gitignore — secrets
   .env
   .env.*
   !.env.example    # allow the template, block actual values
   *.pem
   *.key
   *.p12
   *.pfx
   secrets.json
   credentials.json
   service-account.json
   terraform.tfvars
   *.tfstate
   ```
   Also add `.envrc` (direnv), `kubeconfig`, and any tool-specific credential files.

7. **Use a secrets manager in code, not environment variable files.** The root cause of secrets in code is convenience — it is easier to paste a key than to set up proper secrets management. Invest in making the secure path easy:
   ```ts
   // AWS Secrets Manager
   import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';
   const client = new SecretsManagerClient({ region: 'us-east-1' });
   const { SecretString } = await client.send(new GetSecretValueCommand({ SecretId: 'prod/myapp/stripe' }));
   const { stripeKey } = JSON.parse(SecretString!);
   ```
   For local development: use a `.env` file (in `.gitignore`) that references secrets from your local vault or is populated via `vault read secret/myapp` → `.env`.

8. **Audit repository history on new team member onboarding.** Run `trufflehog` or `gitleaks` on the full Git history of any repository a new team inherits:
   ```sh
   trufflehog git file://. --only-verified
   gitleaks detect --source . --log-opts="--all"
   ```
   Address any historical leaks before adding new secrets to the system.

## References
- Trufflehog (trufflesecurity/trufflehog) — entropy-based secret scanner
- Gitleaks (gitleaks/gitleaks) — SAST for secrets
- `git filter-repo` (newren/git-filter-repo)
- GitHub Secret Scanning documentation
- GitGuardian (gitguardian.com) — continuous secret monitoring
