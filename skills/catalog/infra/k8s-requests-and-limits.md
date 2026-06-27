---
name: k8s-requests-and-limits
description: Set correct CPU/memory requests and limits on Kubernetes pods to ensure scheduling quality, prevent OOMKill, and enable autoscaling.
discipline: infra
tags: [kubernetes, resources, scheduling, oomkill, autoscaling]
---

# Kubernetes Resource Requests and Limits

## When to use

Pods are OOMKilled under load. Node CPU is heavily throttled. HPA cannot scale because requests are
unset (HPA uses requests to compute CPU utilization percentage). A noisy-neighbor pod is consuming
all CPU on a node, starving other pods. Pods are evicted during node pressure events because their
actual resource usage far exceeds their requests.

## Signal

- `kubectl describe pod <name>` shows `OOMKilled` in the last state or reason.
- `kubectl top pod` shows CPU at 1000m (1 core) but CPU limit is 500m — constant throttling.
- HPA output shows `<unknown>` for CPU metric: `Metrics: cpu: <unknown> / 70%` — requests not set.
- `kubectl describe node <name>` shows resource pressure events or eviction messages.
- No `resources:` block in pod/container spec in manifests — unset by default.
- CPU throttle rate metric (`container_cpu_throttled_seconds_total`) is high (>20% of wall time).

## Why

`requests` are what Kubernetes uses for **scheduling** — the scheduler ensures a node has enough
unallocated resources to accommodate the pod's request. Without requests, all pods are scheduled as
if they need zero resources, leading to severe overcommit and eviction cascades when actual usage is
high.

`limits` are enforcement mechanisms: memory limits are hard — exceed them and the process is killed
(OOMKill); CPU limits are soft — exceed them and the kernel throttles the process (not killed, but
slowed). An improperly set CPU limit causes CPU throttling even when the node has plenty of idle
CPU, harming latency-sensitive services.

## Remediate

1. **Set `requests` equal to the typical (p50) resource usage of the container.** Measure actual
   usage with `kubectl top pod` or Prometheus `container_cpu_usage_seconds_total` and
   `container_memory_working_set_bytes`. Do not guess — measure over a representative period.

2. **Set `limits.memory` to requests.memory * 1.5.** This gives headroom for traffic spikes without
   wasting reservation. For memory-sensitive apps with unpredictable spikes, consider setting
   `limits.memory = requests.memory` (Guaranteed QoS class) to avoid OOMKill at the expense of
   no headroom.

3. **Be cautious with CPU limits.** A pod hitting its CPU limit is throttled even if the node has
   idle CPU. For latency-sensitive services: consider setting no CPU limit (only a request). This
   allows burst CPU usage when available. If you must set a limit, use at least 2x the CPU request.

4. **Use VPA (Vertical Pod Autoscaler) in recommendation mode** to calibrate initial values:
   ```bash
   kubectl apply -f vpa.yaml  # mode: "Off" — recommendation only
   kubectl describe vpa <name>  # Shows recommended requests/limits
   ```
   Do not use VPA and HPA on the same deployment (conflict unless using custom metrics for HPA).

5. **Set resources on every container, including init containers and sidecars.**
   ```yaml
   resources:
     requests:
       cpu: "250m"
       memory: "256Mi"
     limits:
       memory: "384Mi"
       # cpu limit intentionally omitted for latency-sensitive workload
   ```

6. **Set a LimitRange in each namespace** to enforce default resource requirements for pods that
   don't specify them:
   ```yaml
   apiVersion: v1
   kind: LimitRange
   metadata:
     name: default-limits
   spec:
     limits:
     - type: Container
       default:
         memory: "256Mi"
       defaultRequest:
         cpu: "100m"
         memory: "128Mi"
   ```

7. **Understand QoS classes and their eviction priority.**
   - **Guaranteed**: `requests == limits` for all resources. Highest priority — never evicted under
     normal pressure.
   - **Burstable**: `requests < limits`. Evicted after BestEffort.
   - **BestEffort**: no requests or limits. Evicted first.
   Critical system components should be Guaranteed QoS.

## References

- Kubernetes documentation: Resource Management for Pods and Containers
- Kubernetes documentation: Pod Quality of Service Classes
- Vertical Pod Autoscaler (github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
- `container_cpu_throttled_seconds_total` Prometheus metric
