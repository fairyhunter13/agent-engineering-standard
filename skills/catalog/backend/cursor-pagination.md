---
name: cursor-pagination
description: Replace offset-based pagination with cursor/keyset pagination to avoid performance degradation at high offsets.
discipline: backend
tags: [api, pagination, database, performance, rest]
---

# Cursor-Based Pagination

## When to use

API returns paginated lists of records. Page N queries become increasingly slow as N grows. `OFFSET`
in SQL climbs in proportion to the page number. Data sets are large (>10,000 rows) or growing.
Real-time feeds where new items can be inserted between page fetches are especially affected.

## Signal

- `EXPLAIN ANALYZE` shows large `OFFSET` values causing the engine to scan and discard rows before
  returning results — visible as `rows removed by filter` or a high `actual rows` on a top-level
  scan that far exceeds the returned row count.
- Response time for page 1 is 10 ms; page 100 is 500 ms; page 1000 is 5 s — linear growth with
  offset size.
- "Last page" or "jump to page N" queries time out in production.
- APM shows DB query time is the dominant contributor to late-page latency.
- Clients report missing or duplicated items when new records are inserted between pages (the
  page-drift problem inherent to offset pagination).

## Why

`OFFSET N` is not a pointer — it is an instruction to the database engine to compute and discard the
first N rows before returning results. Even with an index, the engine must traverse N index entries
to find the starting point. At N=100,000 this scan is significant regardless of how fast the
underlying index operations are.

Keyset/cursor pagination avoids this by using a stable row boundary. Instead of "give me rows 1001
to 1100", it says "give me the 100 rows whose `id` is greater than 1000". The engine uses the index
to jump directly to that point — O(log N) regardless of how deep in the list the cursor is.

Additionally, offset pagination suffers from page drift: inserts or deletes between page fetches
shift the offset boundary, causing items to appear twice or be skipped. Cursors are immune because
they track position by value, not by count.

## Remediate

1. **Replace `LIMIT x OFFSET y` with a keyset WHERE clause:**
   ```sql
   -- Before (offset):
   SELECT * FROM orders ORDER BY id LIMIT 20 OFFSET 100;

   -- After (keyset):
   SELECT * FROM orders WHERE id > :last_id ORDER BY id ASC LIMIT 20;
   ```

2. **Return `next_cursor` (the last-seen ID or composite key) in the API response.** Encode it
   opaquely (base64 or JWT-signed) so clients cannot forge or manipulate the cursor value:
   ```json
   {
     "data": [...],
     "next_cursor": "eyJpZCI6IDEwMjB9",
     "has_next_page": true
   }
   ```

3. **Ensure the cursor columns are indexed.** The `WHERE id > :last_id ORDER BY id` pattern requires
   an index on `id`. For multi-column cursors, the index must cover all cursor columns in order.

4. **Handle multi-column sort with a composite cursor.** When sorting by `(created_at DESC, id ASC)`
   (to handle ties on `created_at`):
   ```sql
   WHERE (created_at, id) < (:last_created_at, :last_id)
   ORDER BY created_at DESC, id ASC
   LIMIT 20;
   ```
   Encode both values in the cursor token.

5. **Provide `has_next_page` boolean.** Fetch `LIMIT + 1` rows; if you get `LIMIT + 1` rows, set
   `has_next_page = true` and return only the first `LIMIT` rows. This avoids a separate `COUNT`
   query.

6. **Document that cursors are opaque and short-lived.** Cursors may expire (e.g., after 24 h if the
   underlying data changes significantly). Clients should not store cursors beyond a single session.
   Do not promise backward compatibility on cursor format.

7. **For APIs that require random access (jump to page N):** Accept that this cannot be done
   efficiently with keyset pagination on large tables. Offer a `total_count` only as a separate
   optional call with an appropriate cost warning. Most product needs do not actually require jumping
   to arbitrary pages.

## References

- PostgreSQL documentation: Row Comparators for multi-column keyset
- Slack Engineering Blog: How Slack handles cursor-based pagination
- GraphQL Cursor Connections Specification (Relay)
- Markus Winand: Pagination Done the Right Way (use-the-index-luke.com)
