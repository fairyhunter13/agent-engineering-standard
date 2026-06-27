---
name: delivery-semantics
description: Understand and correctly implement at-most-once, at-least-once, and exactly-once message delivery semantics.
discipline: backend
tags: [messaging, kafka, reliability, idempotency, distributed-systems]
---

# Message Delivery Semantics

## When to use

Choosing broker configuration and consumer design for a new messaging integration. Preventing
duplicate processing in a financial or inventory workflow. Debugging missing or duplicated events
under failure conditions. Deciding between broker-level guarantees and application-level
deduplication.

## Signal

- Duplicate records appearing in the database after a consumer restart or rebalance.
- Missing events: records that should have been processed were silently dropped during a broker
  outage or consumer crash.
- Lost-update bugs in consumer processing — the consumer updates a counter but produces the wrong
  final value under concurrent processing.
- Inconsistent consumer offsets after a crash — some messages processed twice, some not at all.
- Team debate over "is this a broker configuration issue or a consumer bug?"

## Why

Network partitions, crashes, and timeouts mean that any messaging system faces a choice: when in
doubt, redeliver (at-least-once) or drop (at-most-once). There is no reliable way to guarantee
exactly-once delivery at the network layer alone — it requires coordination between producer,
broker, and consumer.

The practical implication: exactly-once is expensive (transactional coordination), at-least-once is
the safe default (requires idempotent consumers), and at-most-once is only appropriate where loss
is acceptable (metrics, logging). Choosing the wrong semantic for a financial workflow causes
invisible data corruption.

## Remediate

1. **At-most-once (fire-and-forget).**
   - Producer: send without acknowledgment (`acks=0` in Kafka).
   - Consumer: ack (commit offset) before processing.
   - Risk: message lost if producer crashes after send, or consumer crashes after ack but before
     processing.
   - Use for: application-level metrics, analytics events, low-value notifications where occasional
     loss is acceptable.

2. **At-least-once (the safe default).**
   - Producer: send with `acks=all` (Kafka) — wait for all ISR replicas to acknowledge.
   - Consumer: commit offset only after successful processing. If processing fails, the message is
     redelivered.
   - Risk: a crash between processing and offset commit causes redelivery — duplicates are possible.
   - Requires: idempotent consumer — processing the same message twice produces the same result.
   - Use for: most workloads. Combine with idempotency keys (event ID dedup) for correctness.

3. **Exactly-once (transactions).**
   - Kafka configuration:
     ```
     enable.idempotence=true          # producer: exactly-once per partition
     transactional.id=<unique-id>     # producer: enable transactions
     isolation.level=read_committed   # consumer: only read committed messages
     ```
   - Consumer: wrap processing and offset commit in a single Kafka transaction (read-process-write
     atomic). Or use the consume-transform-produce pattern with Kafka Streams.
   - Cost: higher latency, lower throughput, more complex consumer code, requires broker version
     support.
   - Use for: stream processing pipelines where idempotency cannot be guaranteed at the application
     layer (e.g., non-idempotent aggregations).

4. **For most production workloads: at-least-once + idempotent consumer is the correct choice.**
   The implementation pattern:
   ```python
   def process_message(msg):
       if idempotency_store.exists(msg.id):
           return  # already processed
       with db.transaction():
           apply_business_logic(msg)
           idempotency_store.mark_done(msg.id)
   ```
   Use a DB unique constraint or Redis `SET NX` for the idempotency store. TTL the store entries
   after the redelivery window (e.g., 7 days).

5. **Test delivery semantics explicitly.**
   - Simulate consumer crash mid-processing: verify no data loss and no duplicate records.
   - Simulate duplicate delivery: verify idempotent handling.
   - Use Kafka's `kafka-consumer-groups.sh --reset-offsets` to replay and test reprocessing.

6. **Document the delivery semantic and idempotency contract** for every consumer in the system. It
   should be visible in the consumer's README or interface definition.

## References

- Martin Kleppmann — *Designing Data-Intensive Applications*, Chapter 11
- Apache Kafka documentation: Exactly-Once Semantics, Idempotent Producer
- Jay Kreps: "The Log: What every software engineer should know about real-time data's unifying
  abstraction" (engineering.linkedin.com)
