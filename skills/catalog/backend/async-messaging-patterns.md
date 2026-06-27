---
name: async-messaging-patterns
description: Decouple services using message queues and async patterns to improve resilience, scalability, and service independence.
discipline: backend
tags: [messaging, kafka, async, microservices, distributed-systems]
---

# Async Messaging Patterns

## When to use

Synchronous coupling between services causes cascading failures. A long-running operation blocks an
HTTP response. One service produces events that multiple downstream consumers need to process
independently. Processing throughput must scale independently of the producer. Work must survive a
downstream service being temporarily unavailable.

## Signal

- HTTP request timeout errors caused by a downstream service being slow — the calling service is
  unavailable because of a dependency.
- P99 latency of one service tightly tracks the P99 latency of its downstream dependencies.
- A downstream outage causes 5xx errors in the upstream service even for operations that don't need
  an immediate response.
- A new consumer requirement means adding a new synchronous call into an existing hot path.
- Job processing needs to scale out independently of the web tier.

## Why

Synchronous HTTP calls couple the availability of two services: if Service B is slow, Service A
blocks; if Service B is down, Service A fails. This coupling propagates failures upward through a
call chain. Async messaging breaks this dependency: Service A writes a message and returns
immediately; Service B processes it when ready. A temporary outage of Service B does not affect
Service A's availability.

Beyond resilience, messaging enables fanout (one producer, many consumers), backpressure
(consumers process at their own rate), and replay (reprocess historical events). These patterns are
fundamental to scalable distributed systems.

## Remediate

1. **Identify operations that are safe to make async.** Good candidates:
   - Side effects that don't need to complete before the HTTP response: email sending, push
     notifications, analytics events, search index updates.
   - Long-running jobs: PDF generation, batch imports, ML inference.
   - Fanout: an order created event consumed by billing, inventory, and fulfillment independently.
   Operations that must complete synchronously (e.g., returning a payment authorization to the user)
   are not candidates.

2. **Choose a broker appropriate to the workload.**
   - **Kafka**: high-throughput ordered streams, event replay, log compaction, multi-consumer groups.
     Use for event sourcing, audit logs, and stream processing.
   - **SQS** (AWS): simple, fully managed, at-least-once delivery. Best for task queues without
     ordering requirements.
   - **RabbitMQ**: flexible routing via exchanges, dead-letter queues, lower throughput than Kafka.
     Best for work queues with complex routing.

3. **Design consumers for idempotency.** Brokers that guarantee at-least-once delivery will
   occasionally deliver duplicates. Every consumer must be safe to run twice on the same message.
   Use the message ID as an idempotency key, deduplicated in a DB table or Redis `SET NX`.

4. **Configure dead-letter queues (DLQ) for every consumer.** When a message fails processing after
   N retries, route it to a DLQ rather than discarding. Alert on DLQ depth > 0. Inspect DLQ messages
   to diagnose consumer bugs.

5. **Use the outbox pattern for transactional publishing.** Never publish to a broker inside an
   application transaction — if the transaction commits but the broker call fails, the event is lost.
   Instead:
   - Write the event to an `outbox` table in the same DB transaction as the business change.
   - A background relay reads undelivered outbox rows and publishes them to the broker.
   - Mark rows as delivered after successful publish.
   This guarantees the event is published if and only if the business transaction commits.

6. **Set consumer concurrency and prefetch limits.** Unbounded prefetch can exhaust consumer memory.
   Set `max_in_flight` / `prefetch_count` to a value the consumer can process without OOM. Scale
   consumer instances horizontally (Kafka: more partitions; SQS: more consumer instances).

7. **Trace messages across the async boundary.** Propagate the `traceparent` (W3C Trace Context) in
   the message headers so distributed traces span the async hand-off. Without this, a slow consumer
   appears as a gap in the trace.

## References

- Martin Kleppmann — *Designing Data-Intensive Applications*, Chapter 11 (Stream Processing)
- Enterprise Integration Patterns (Hohpe & Woolf) — Message Channel, Dead Letter Channel
- Outbox pattern (microservices.io/patterns/data/transactional-outbox.html)
- Kafka documentation: Consumer Groups, Idempotent Producer
