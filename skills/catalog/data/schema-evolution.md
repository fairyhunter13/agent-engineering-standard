---
name: schema-evolution
description: Evolve message and data-lake schemas without breaking producers or consumers in flight.
discipline: data
tags: [data, schema, avro, protobuf, backward-compatibility]
---

# Schema Evolution

## When to use
Evolving a message schema in Kafka or an event bus; changing a Parquet/Avro data lake schema; rolling out new fields or removing deprecated ones.
Apply this any time a schema change could affect a system component that you do not deploy simultaneously with the producer.

## Signal
- Consumers break or throw deserialization exceptions when the producer adds a new field.
- A schema change requires a simultaneous deploy of the producer and every consumer — a "flag day."
- No schema registry in use; schemas are managed as ad-hoc JSON or documented only in a wiki.
- Old consumers silently drop new fields or produce incorrect aggregates because they read stale schemas.
- Avro/Protobuf files are modified without versioning, making it impossible to decode historical data.

## Why
In event-driven systems, producers and consumers evolve independently on different release cadences.
A breaking schema change triggers cascading failures: consumers that cannot deserialize messages fall behind, dead-letter queues fill up, and data is lost or delayed.
Schema compatibility guarantees are the formal contract between producer and consumer that allows independent deployment.
Without a registry, the schema is implicit — the first mismatch discovered in production is the first time anyone knows the contract was broken.

## Remediate
1. **Use a schema registry**: Deploy Confluent Schema Registry, AWS Glue Schema Registry, or Apicurio. Producers register schemas before publishing; consumers fetch schemas by ID embedded in the message envelope. The registry enforces configured compatibility modes at publish time.
2. **Safe Avro changes**: Adding an optional field with a default value is always safe (`"default": null`). Removing a field breaks backward compatibility — mark it deprecated, wait for consumers to ignore it, then remove. Never rename a required field; add a new one and migrate.
3. **Safe Protobuf changes**: Adding a new optional field with a new field number is safe. Removing a field: reserve the field number with `reserved` to prevent future reuse. Never change a field's type or number.
4. **Set the right compatibility mode** in the registry:
   - `BACKWARD`: new schema can read data written with the old schema (safest for consumer rollout).
   - `FORWARD`: old schema can read data written with the new schema (safe for producer-first rollout).
   - `FULL`: both directions (best for independent deployments).
5. **Expand-contract migration** for breaking changes: (a) expand — add the new field alongside the old one; (b) migrate consumers to read the new field; (c) migrate producers to write both; (d) contract — remove the old field once all consumers are updated.
6. **Version in topic names for major changes**: `orders.v1`, `orders.v2`. Run both topics in parallel during migration; route consumers progressively from v1 to v2; decommission v1 after full cutover.

## References
- Confluent Schema Registry documentation — compatibility types
- Martin Kleppmann, *Designing Data-Intensive Applications*, Chapter 4: Encoding and Evolution
- Protobuf Language Guide: Field Numbers and Reserved Fields
- Avro Specification: Schema Resolution rules
- Expand-contract (parallel change) pattern — Martin Fowler
