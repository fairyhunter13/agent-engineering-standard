---
name: horizontal-pod-autoscaling
description: Configure Kubernetes HPA (and KEDA) to scale deployments based on CPU, memory, or custom metrics to handle variable load.
discipline: infra
tags: [kubernetes, autoscaling, hpa, keda, reliability]
---

# Horizontal Pod Autoscaling

## When to use

Traffic is bursty and statically-scaled deployments over-provision during off-peak (wasted cost) or
under-provision during peaks (latency spikes or errors). The team manually adjusts replica counts
before expected traffic events. Autoscaling is already configured but pods are not scaling out
quickly enough or flapping (scaling up and down repeatedly).

## Signal

- CPU utilization sustained >80% with no scale-out occurring — HPA not configured or metrics not
  available.
- HPA `kubectl describe hpa <name>` shows: `ScalingActive: false` with reason
  `FailedGetScale` or `DesiredReplicas: 1 CurrentReplicas: 1` with CPU showing `<unknown>`.
- `minReplicas` equals `maxReplicas` — effectively disabling autoscaling.
- Flapping: pods scale out then back in within minutes, repeatedly — stabilization window too short.
- Off-peak: `kubectl top pod` shows nearly idle pods at minimum replica count — fine, but cost is
  high if minimum is set too high.
- Queue depth (for worker services) grows without triggering scale-out — HPA uses only CPU metric,
  not queue depth.

## Why

Static replica counts are a compromise between cost (over-provisioned off-peak) and reliability
(under-provisioned at peak). HPA closes this loop by observing actual utilization and adjusting
replica count dynamically. The result: capacity tracks load without manual intervention, SLOs are
maintained at peak, and cost is reduced at off-peak.

KEDA (Kubernetes Event-Driven Autoscaling) extends HPA with event source triggers — scaling to zero
and scaling based on queue depth, database row counts, or external metrics — enabling true scale-to-
zero for batch workloads.

## Remediate

1. **Prerequisites: set `resources.requests.cpu` on the target container.** HPA `cpu` metric is
   `current_cpu_usage / requested_cpu`. If requests are not set, HPA cannot compute CPU utilization
   percentage and reports `<unknown>`:
   ```yaml
   resources:
     requests:
       cpu: "250m"
       memory: "256Mi"
   ```

2. **Create an HPA using `kubectl autoscale` or a manifest.**
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: myapp
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: myapp
     minReplicas: 2
     maxReplicas: 20
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```
   Target 70% CPU utilization — leaves 30% headroom for traffic spikes before scaling.

3. **Set `minReplicas: 2` for production services** (never 1 — a single pod is a single point of
   failure during node drain or pod eviction).

4. **Configure scale-down stabilization to prevent flapping.**
   ```yaml
   behavior:
     scaleDown:
       stabilizationWindowSeconds: 300   # 5-minute stabilization before scale-down
       policies:
       - type: Percent
         value: 10
         periodSeconds: 60              # Remove at most 10% of pods per minute
   scaleUp:
     stabilizationWindowSeconds: 0      # Scale up immediately
     policies:
     - type: Percent
       value: 100
       periodSeconds: 15               # Can double replica count every 15s
   ```

5. **Use KEDA for event-driven scaling** (queue depth, Kafka lag, database row count, etc.):
   ```yaml
   apiVersion: keda.sh/v1alpha1
   kind: ScaledObject
   metadata:
     name: myworker
   spec:
     scaleTargetRef:
       name: myworker
     minReplicaCount: 0   # scale to zero when idle
     maxReplicaCount: 50
     triggers:
     - type: aws-sqs-queue
       metadata:
         queueURL: https://sqs.us-east-1.amazonaws.com/123/myqueue
         queueLength: "10"   # 1 pod per 10 messages in queue
   ```

6. **Add custom metrics for better scaling signal.** CPU is a proxy metric; RPS (requests per
   second) or P99 latency are better signals for web services. Use Prometheus Adapter to expose
   Prometheus metrics to HPA.

7. **Validate with a load test.** Run a load test in staging that drives CPU above the target
   threshold. Observe: pods scale out within 30–60 s; scale-down takes 5+ min (stabilization
   window); max replicas is sufficient to handle the peak load without throttling.

## References

- Kubernetes documentation: Horizontal Pod Autoscaling
- KEDA documentation (keda.sh)
- Kubernetes documentation: HPA `behavior` field
- Prometheus Adapter: Custom Metrics API for HPA
