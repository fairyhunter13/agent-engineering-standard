---
name: liveness-and-readiness-probes
description: Configure Kubernetes liveness, readiness, and startup probes correctly to enable self-healing and safe traffic routing.
discipline: infra
tags: [kubernetes, health-checks, probes, reliability, deployment]
---

# Kubernetes Liveness, Readiness, and Startup Probes

## When to use

Traffic is routed to pods before they are ready to serve, causing 503s or connection errors during
deployments. Pods are being restarted unnecessarily by an overly aggressive liveness probe. The
application takes 30+ seconds to start but the liveness probe kills it after 10 seconds. A pod
appears Running but is actually deadlocked — and nothing detects it.

## Signal

- 503 errors spike during rolling deployments — traffic is routed to new pods before they are
  initialized.
- `kubectl describe pod` shows `CrashLoopBackOff` with `Liveness probe failed: HTTP probe failed
  with status code 503` — the probe fires during startup.
- Readiness probe checks a downstream dependency (e.g., DB connectivity) that is temporarily
  unavailable, causing pods to become not-Ready unnecessarily.
- Pods in `Running` state but not actually serving traffic — stuck in an internal deadlock that no
  probe detects.
- `kubectl describe pod` shows `Readiness probe failed` during a cold start when the service is
  legitimately still initializing.

## Why

Kubernetes uses these probes for two distinct purposes that must never be conflated:
- **Readiness**: controls whether a pod receives traffic. A not-Ready pod is removed from Service
  endpoints. This must reflect whether the pod can handle requests *right now*.
- **Liveness**: controls whether a pod should be restarted. A failed liveness probe triggers a
  restart. This must only fail on irrecoverable conditions — not during startup, not on dependency
  failures.
- **Startup**: prevents liveness and readiness from firing during initial startup. Essential for
  slow-starting JVM applications, ML model loading, or database migration runs.

Mixing these responsibilities — e.g., checking DB connectivity in a liveness probe — causes cascading
restarts during DB slowness, which amplifies the outage.

## Remediate

1. **Implement a `/healthz` endpoint with three distinct behaviors.**
   Expose the same path or separate paths for each probe type:
   ```
   GET /healthz/live   → 200 if process is alive and not deadlocked (no external deps)
   GET /healthz/ready  → 200 if ready to serve (DB connected, cache warm, migrations done)
   GET /healthz/start  → 200 if initial startup is complete
   ```

2. **Configure a startup probe for slow-starting applications.** This prevents liveness from
   killing the app during initialization:
   ```yaml
   startupProbe:
     httpGet:
       path: /healthz/start
       port: 8080
     failureThreshold: 30    # 30 * 10s = 5 minutes max startup time
     periodSeconds: 10
   ```
   Once the startup probe succeeds, Kubernetes activates liveness and readiness probes.

3. **Keep the liveness probe lightweight.** It should check only in-process state — an in-memory
   flag, goroutine health, or a dead-simple HTTP response. Never check downstream dependencies in
   liveness:
   ```yaml
   livenessProbe:
     httpGet:
       path: /healthz/live
       port: 8080
     initialDelaySeconds: 0  # startup probe handles initial delay
     periodSeconds: 10
     failureThreshold: 3
     timeoutSeconds: 5
   ```

4. **Readiness probe may check dependencies, but thoughtfully.** It is acceptable to mark a pod not-
   Ready when the DB is unreachable — this prevents routing traffic to a pod that cannot serve it.
   However, also consider: if the DB is down, no pod will be Ready, which may be correct behavior
   (fail closed) or may cause a complete service outage. Set `failureThreshold` generously (≥3) to
   tolerate transient DB hiccups:
   ```yaml
   readinessProbe:
     httpGet:
       path: /healthz/ready
       port: 8080
     periodSeconds: 5
     failureThreshold: 3
     successThreshold: 1
   ```

5. **Use `httpGet` probes rather than `exec` probes when possible.** `exec` probes spawn a new
   process per probe check — expensive at scale. `httpGet` and `tcpSocket` probes are handled by
   kubelet in-process.

6. **Set `initialDelaySeconds` only if you do not have a startup probe.** If you have a startup
   probe, `initialDelaySeconds` on liveness/readiness should be 0.

7. **Test probe behavior during deployment.** Run a rolling deployment and monitor 5xx rate. Test
   that a process stuck in a deadlock (sleeping thread) is detected by the liveness probe within
   `failureThreshold * periodSeconds` seconds.

## References

- Kubernetes documentation: Configure Liveness, Readiness, and Startup Probes
- Kubernetes documentation: Pod Lifecycle
- Google SRE Workbook: Health Checking
