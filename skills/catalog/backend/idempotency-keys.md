---
name: idempotency-keys
description: Make mutating API endpoints safe to retry without duplicate side effects by implementing idempotency keys.
discipline: backend
tags: [api, reliability, distributed-systems, payments, retries]
---

# Idempotency Keys

## When to use

Clients retry on network failure or timeout. POST endpoints perform payments, order creation, email
sending, or any other non-idempotent side effect. Any mutating operation where "did it happen?"
is uncertain from the client's perspective requires idempotency key support.

## Signal

- Duplicate charges or records appearing in the database after a client timeout followed by a retry.
- Missing `Idempotency-Key` header support in payment or order creation endpoints.
- No deduplication table or cache in the system — every request is processed regardless of
  whether an identical request was already processed.
- Client SDK or mobile app retries on HTTP 5xx or network error without any deduplication.
- Support tickets reporting double-charged users or duplicate orders after poor network conditions.

## Why

Without idempotency keys, retrying a failed request can create duplicate side effects. The client
has no way to know whether the first request succeeded (it timed out, not failed) — so retrying is
the only safe option. But retrying without deduplication creates duplicates. The solution must live
on the server: accept a client-provided idempotency key, remember it, and return the original
response on duplicate requests without re-executing the operation.

This pattern is not optional for payments and financial operations — it is the baseline standard
mandated by payment networks, enforced by Stripe's API design, and expected by Visa/Mastercard
dispute processes.

## Remediate

1. **Accept an `Idempotency-Key` header (client-generated UUID v4).** Document that clients must
   generate a unique key per intended operation — not per request. The same key should be reused on
   retries of the same logical action.

2. **On first receipt: store the key and the response atomically.**
   ```sql
   -- In the same transaction as the operation:
   INSERT INTO idempotency_records (key, response_status, response_body, created_at)
   VALUES (:key, :status, :body, NOW())
   ON CONFLICT (key) DO NOTHING;
   ```
   If the `INSERT` has 0 affected rows, a duplicate was received — return the stored response
   without re-executing. If 1 row was inserted, proceed with the operation.

3. **Alternative: Redis atomic dedup.** Use `SET key payload NX PX <ttl_ms>` (SET if Not eXists).
   If the key already exists, return the stored payload. Use Lua scripting or Redis transactions to
   make the check-and-set atomic.

4. **Return the original response on duplicate, not a 409 Conflict.** The caller does not know
   whether the original succeeded — a 2xx with the original response body is the correct answer.
   Optionally add `Idempotency-Replayed: true` response header for observability.

5. **Set TTL appropriate to the use case.**
   - Payments: 24 hours (Stripe's standard).
   - Order creation: 1 hour.
   - General mutations: configurable, default 24 hours.
   Purge expired records via a background job.

6. **Handle partial failures.** If the operation partially executed before the server crashed, the
   next request with the same key should detect the partially-created record and either complete it
   or return an error. Design operation steps to be atomic using DB transactions.

7. **Scope keys to the authenticated caller.** The dedup table should include the `user_id` or
   `api_key_id` alongside the idempotency key to prevent cross-client key collisions.

8. **Return a clear error for invalid key reuse.** If the same key is submitted with different
   request parameters (e.g., different amount), return `422 Unprocessable Entity` — same key with
   different payload is a client programming error.

## References

- Stripe API documentation: Idempotent requests
- AWS payment best practices: Idempotency in distributed systems
- RFC 9110 — HTTP Semantics (safe vs. idempotent methods)
- Martin Kleppmann — *Designing Data-Intensive Applications*, Chapter 11
