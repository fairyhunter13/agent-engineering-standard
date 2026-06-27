---
name: zero-downtime-deployments
description: Ensure application deployments complete without any dropped requests, failed health checks, or visible errors to end users.
discipline: infra
tags: [kubernetes, deployment, reliability, devops, rolling-update]
---

# Zero-Downtime Deployments

## When to use

Deployments cause brief 5xx spikes or connection reset errors visible in APM. Load balancers route
traffic to pods that are starting up or shutting down. Scheduled maintenance windows are required
for routine releases. `kubectl rollout status` shows a period with fewer than minimum required Ready
pods during rollout.

## Signal

- 5xx rate spike in APM aligned precisely with deployment timestamps.
- Client-side connection reset errors during deploys — clients see `ECONNRESET` or `502 Bad Gateway`.
- `kubectl rollout status` shows zero Ready pods during the transition from old to new pod.
- `kubectl describe pod` shows old pod terminated immediately on SIGTERM with in-flight requests
  still being processed.
- Startup probe not configured — liveness probe kills the new pod before it initializes.
- Database migrations run in the same process as the application startup, blocking readiness.

## Why

A deployment cycle involves terminating old pods and starting new ones. Without careful
configuration, there is a window where: (a) traffic is routed to new pods before they are ready, or
(b) traffic is routed to old pods that have already received SIGTERM and are shutting down. Either
causes 503s or connection resets.

Kubernetes provides all the mechanisms to eliminate this window — rolling update strategy, readiness
probes, and preStop hooks — but they must be explicitly configured. The defaults are not sufficient
for zero-downtime.

## Remediate

1. **Use rolling update strategy with `maxUnavailable=0` and `maxSurge=1`.**
   ```yaml
   spec:
     strategy:
       type: RollingUpdate
       rollingUpdate:
         maxUnavailable: 0   # never reduce below desired count
         maxSurge: 1         # allow one extra pod during rollout
   ```
   This ensures that the old pod is only terminated after the new pod is Ready. At `maxUnavailable:
   0`, there is always at least `replicas` pods serving traffic.

2. **Configure readiness probes.** Kubernetes only routes traffic to a pod when its readiness probe
   passes. The new pod must be Ready before the old pod is terminated. See
   `infra/liveness-and-readiness-probes` for detailed probe configuration. At minimum:
   ```yaml
   readinessProbe:
     httpGet:
       path: /healthz/ready
       port: 8080
     periodSeconds: 5
     failureThreshold: 3
   ```

3. **Add a `preStop` hook to drain in-flight requests before SIGTERM.**
   When Kubernetes terminates a pod, it removes the pod from Service endpoints and then sends
   SIGTERM. However, there is a race condition — some requests may already be en-route to the pod
   when it is de-registered. A `preStop` sleep gives the load balancer time to stop routing new
   requests:
   ```yaml
   lifecycle:
     preStop:
       exec:
         command: ["/bin/sh", "-c", "sleep 5"]
   ```
   This adds a 5-second drain window before the application receives SIGTERM.

4. **Set `terminationGracePeriodSeconds` ≥ preStop duration + max request duration + buffer.**
   If your slowest request takes 30 seconds and preStop sleeps 5 seconds:
   ```yaml
   terminationGracePeriodSeconds: 45   # 5s preStop + 30s max request + 10s buffer
   ```
   After this period, Kubernetes sends SIGKILL regardless of in-flight requests.

5. **Handle SIGTERM gracefully in your application code.** On receiving SIGTERM:
   - Stop accepting new connections (close the listening socket).
   - Allow in-flight requests to complete.
   - Flush logs and metrics.
   - Exit cleanly.
   Most HTTP server frameworks (gin, express, Spring Boot) support graceful shutdown with a simple
   configuration:
   ```go
   // Go: graceful shutdown
   srv.Shutdown(ctx)  // waits for active connections to close
   ```

6. **Run database migrations as a pre-deploy Kubernetes Job, not in application startup.**
   ```yaml
   # Helm pre-upgrade hook
   apiVersion: batch/v1
   kind: Job
   metadata:
     annotations:
       helm.sh/hook: pre-upgrade
       helm.sh/hook-weight: "-5"
   spec:
     template:
       spec:
         containers:
         - name: migrate
           command: ["./migrate", "up"]
   ```
   Application startup must not run migrations — it blocks readiness, causes multiple migrations on
   multi-pod deploys, and fails the zero-downtime model.

7. **Verify with a live rollout test.** Run a deployment in staging while sending load:
   ```bash
   # Terminal 1: watch rollout
   kubectl rollout status deployment/myapp -w

   # Terminal 2: continuous request (watch for errors)
   while true; do curl -s -o /dev/null -w "%{http_code}\n" http://staging.myapp.com/; done
   ```
   You should see no non-2xx responses during the rollout. Any `000` (connection refused) or `503`
   indicates a gap in the configuration.

## References

- Kubernetes documentation: Deployments, Rolling Update Strategy
- Kubernetes documentation: Pod Lifecycle, Container Lifecycle Hooks
- Kubernetes documentation: `terminationGracePeriodSeconds`
- Argo Rollouts: for canary and blue-green as more advanced zero-downtime strategies
