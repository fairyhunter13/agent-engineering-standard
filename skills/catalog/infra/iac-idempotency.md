---
name: iac-idempotency
description: Write Infrastructure-as-Code (Terraform, Pulumi, Helm) that is fully idempotent and safe to re-run without side effects.
discipline: infra
tags: [terraform, pulumi, iac, devops, idempotency]
---

# IaC Idempotency

## When to use

An `apply` or `deploy` operation fails partway through and leaves infrastructure in an inconsistent
state. Re-running the same plan creates duplicate resources or errors rather than converging to the
desired state. IaC is modified outside the codebase (manual console changes) causing drift. Multiple
team members apply changes and encounter state conflicts.

## Signal

- `terraform apply` succeeds on first run but errors on second: `Error: resource already exists`.
- Manual changes in the cloud console cause `terraform plan` to show unexpected replacements.
- `terraform state` shows resources not in code, or code describes resources not in state.
- State file stored locally — different engineers have different state views.
- `terraform apply` on a partially-failed apply shows "nothing to do" when there are clearly
  resources missing.
- Helm `install` fails on re-run because the release name already exists (should use `upgrade --install`).

## Why

Idempotent IaC means applying the same configuration multiple times produces the same result as
applying it once. When an apply fails midway, the next apply must complete the remaining work
without duplicating what succeeded. Non-idempotent IaC forces manual intervention after every
partial failure — blocking recovery and making automation unreliable.

Infrastructure drift (live resources diverging from code) is the other failure mode: manual console
changes are not tracked, the next apply is a surprise, and team members cannot trust `plan` output.

## Remediate

1. **Store Terraform state in a remote, locked backend.**
   ```hcl
   terraform {
     backend "s3" {
       bucket         = "myorg-terraform-state"
       key            = "production/terraform.tfstate"
       region         = "us-east-1"
       dynamodb_table = "terraform-lock"
       encrypt        = true
     }
   }
   ```
   DynamoDB provides state locking — prevents concurrent applies. GCS with `prefix` and
   `bucket` serves the same purpose on GCP.

2. **Run `terraform plan` before every apply in CI.** Treat the plan output as a diff to review.
   Fail CI if the plan is not clean (no unexpected changes). Never apply without reviewing the plan.

3. **Use `terraform import` or `moved` blocks to bring existing resources under management** instead
   of deleting and re-creating them. For Terraform 1.1+, use `moved {}` blocks to rename resources
   without destroying:
   ```hcl
   moved {
     from = aws_s3_bucket.old_name
     to   = aws_s3_bucket.new_name
   }
   ```

4. **Protect critical resources from accidental deletion.**
   ```hcl
   resource "aws_rds_cluster" "main" {
     lifecycle {
       prevent_destroy       = true
       ignore_changes        = [engine_version]
     }
   }
   ```

5. **Avoid `provisioner` blocks.** Provisioners (`local-exec`, `remote-exec`) are not idempotent —
   they re-run on resource recreation. Use cloud-native init scripts (`user_data`, cloud-init) or
   configuration management tools (Ansible, cloud-init) that support idempotent operations.

6. **Run `terraform validate` and `tflint` in CI.** These catch syntax errors and anti-patterns
   before apply. Add `checkov` or `tfsec` for security policy checks.

7. **For Helm: always use `helm upgrade --install --atomic`.**
   - `--install`: creates the release if it doesn't exist; upgrades if it does. Idempotent.
   - `--atomic`: rolls back automatically on failure. The release is never left in a broken state.
   ```bash
   helm upgrade --install --atomic --timeout 5m \
     myapp ./chart --namespace production
   ```

8. **Detect and resolve drift proactively.** Run `terraform plan` on a schedule (daily or weekly in
   CI) and alert if it shows unexpected changes — indicates manual drift has occurred.

## References

- Terraform documentation: Remote backends, State locking, `moved` blocks
- tflint: Terraform linter
- checkov: Policy-as-code for IaC security
- Helm documentation: `upgrade --install`, `--atomic`
