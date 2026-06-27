---
name: least-privilege-and-zero-trust
description: Eliminate implicit trust in service-to-service communication and IAM permissions by applying zero-trust networking, per-workload identities, and minimal IAM policies.
discipline: security
tags: [security, zero-trust, least-privilege, iam, rbac]
---

# Least Privilege and Zero Trust

## When to use
Apply this skill when designing service-to-service authentication, when reviewing IAM permissions, when architecting network security for a microservices deployment, when migrating from a flat network to zero-trust, or when a penetration test finds lateral movement possibilities.

## Signal
- Multiple services share a single database user with full `ALL PRIVILEGES`.
- IAM roles or policies contain `"Action": "*"` or `"Resource": "*"`.
- Services communicate over a flat VPC network with no mTLS or service mesh.
- Services use long-lived static credentials (AWS access keys, static API keys for service-to-service auth) instead of short-lived tokens.
- There is no network policy preventing Service A from calling Service B's internal endpoints directly.
- A compromised service has read access to all other services' secrets.

## Why
"Trust but verify" is the legacy network security model — once inside the perimeter, everything is trusted. Zero trust (NIST SP 800-207, 2020) assumes breach: treat every request as potentially malicious regardless of network origin, and verify identity and authorization on every call. The practical impact: when a service is compromised (and the Verizon DBIR shows that service compromise is when, not if), zero trust limits the blast radius to what that specific service's identity is authorized to do — not the entire infrastructure. Least privilege IAM ensures a compromised service cannot escalate to full cloud account control.

## Remediate

1. **Create per-workload IAM identities.** Each service (Lambda function, ECS task, Kubernetes pod, EC2 instance) must have its own IAM role with only the permissions it needs:
   ```hcl
   # Terraform — per-service IAM role
   resource "aws_iam_role" "order_service" {
     name = "order-service-role"
     assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
   }

   resource "aws_iam_role_policy" "order_service_policy" {
     role = aws_iam_role.order_service.id
     policy = jsonencode({
       Version = "2012-10-17"
       Statement = [{
         Effect   = "Allow"
         Action   = ["s3:GetObject", "s3:PutObject"]
         Resource = "arn:aws:s3:::order-documents-bucket/*"
       }, {
         Effect   = "Allow"
         Action   = ["sqs:SendMessage"]
         Resource = aws_sqs_queue.order_events.arn
       }]
     })
   }
   ```
   The order service has no access to: the user database, billing secrets, admin panels, or other services' S3 buckets.

2. **Use short-lived credentials via OIDC.** Replace long-lived static keys with short-lived tokens:
   - **AWS**: use ECS Task Roles (IRSA on EKS) — credentials auto-rotate every 6–12 hours via AWS STS.
   - **Kubernetes → AWS**: IRSA (IAM Roles for Service Accounts) — pod-level granularity.
   - **CI/CD**: use GitHub Actions OIDC → AWS STS AssumeRoleWithWebIdentity (no static keys in CI).
   - **Service-to-service**: service mesh mTLS or SPIFFE/SPIRE identities.

3. **Implement mTLS between services.** Mutual TLS authenticates both the client and server — not just the server (as in standard TLS). In Kubernetes, use a service mesh:
   - **Istio**: `PeerAuthentication` policy to require mTLS.
   - **Linkerd**: mTLS enabled by default for all pod-to-pod communication.
   ```yaml
   # Istio — require strict mTLS for all services in the namespace
   apiVersion: security.istio.io/v1beta1
   kind: PeerAuthentication
   metadata:
     name: default
     namespace: production
   spec:
     mtls:
       mode: STRICT
   ```

4. **Enforce network micro-segmentation.** Use Kubernetes NetworkPolicies (or cloud security groups) to restrict which services can talk to which:
   ```yaml
   # NetworkPolicy — order service can only receive from gateway; not from other services
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: order-service-ingress
   spec:
     podSelector:
       matchLabels:
         app: order-service
     policyTypes: [Ingress]
     ingress:
       - from:
           - podSelector:
               matchLabels:
                 app: api-gateway
   ```

5. **Apply zero-trust principles at every request.** Zero trust means: verify identity on every request (even internal), authorize the specific action on the specific resource (not just "is this an internal service"), log every access decision. Do not assume that because a request comes from inside the VPC, it is authorized.

6. **Rotate and audit credentials quarterly.** Schedule quarterly reviews:
   - AWS IAM Access Analyzer: identifies overly permissive policies.
   - `cloudsplaining` (Python tool): generates HTML report of IAM permission risks.
   - `iamlive` (in dev/staging): records what IAM permissions your service actually uses → right-size permissions.
   ```sh
   pip install cloudsplaining
   cloudsplaining scan-account --profile my-aws-profile
   ```

7. **Secrets: per-service namespaced paths.** In HashiCorp Vault or AWS Secrets Manager, namespace secrets by service:
   ```
   secret/order-service/database-password
   secret/order-service/stripe-webhook-secret
   # order-service IAM policy grants access to secret/order-service/* only
   # NOT secret/payment-service/* or secret/admin/*
   ```

8. **Implement audit logging for IAM and network access.** Enable:
   - AWS CloudTrail: logs all IAM and API calls.
   - AWS VPC Flow Logs: logs all network traffic (src IP, dst IP, port, protocol, accept/reject).
   - Kubernetes audit logs: logs all API server requests.
   Alert on: cross-service calls outside the defined network policy, IAM role assumption from unexpected entities, elevated privilege requests.

## References
- NIST SP 800-207 — Zero Trust Architecture (2020)
- CISA Zero Trust Maturity Model (2023)
- AWS IAM Access Analyzer
- cloudsplaining (salesforce/cloudsplaining) — IAM policy analyzer
- Istio security documentation (istio.io/docs/concepts/security)
- SPIFFE/SPIRE (spiffe.io) — service identity framework
