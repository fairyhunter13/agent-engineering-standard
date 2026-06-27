---
name: concurrency-and-races
description: Identify and eliminate data races and shared-state bugs in concurrent and async code.
discipline: craft
tags: [concurrency, race-conditions, threads, goroutines, async]
---

# Concurrency and Races

## When to use
Writing goroutines, threads, or async tasks that share mutable state; reviewing code for thread safety; debugging intermittent failures under load that disappear when you add logging.
Apply this whenever two execution contexts could access the same mutable data without coordination.

## Signal
- Tests pass consistently in serial but fail intermittently when run with `-parallel` or under load.
- Data corruption is visible only when the service handles high concurrent request volume.
- The Go race detector (`go test -race`) or Java ThreadSanitizer reports a data race.
- A "heisenbug": the bug disappears when you add logging or a sleep statement, because those introduce implicit synchronization.
- A counter or cache is read and written from multiple goroutines/threads without a lock.
- A struct field is initialized lazily in one goroutine and read from another without synchronization.

## Why
Race conditions cause data corruption that is non-deterministic, non-reproducible under normal conditions, and extremely difficult to debug post-hoc.
They are often discovered in production under peak load — the worst possible time.
Many races are security-relevant: a race on a permission check (TOCTOU — time of check to time of use) can allow unauthorized access.
The fundamental issue is that the hardware and OS scheduler can interleave instructions in any order; without explicit synchronization, every interleaving is possible.

## Remediate
1. **Go: run the race detector in CI always**: `go test -race ./...` must pass before merge. The race detector has low false positive rate; every report it generates is a real race. Fix all races — do not suppress them.
2. **Go: prefer channels over shared memory**: "Do not communicate by sharing memory; instead, share memory by communicating." Use channels to transfer ownership of data between goroutines. Use `sync.Mutex` only when a shared data structure genuinely needs concurrent access.
3. **Java: use `java.util.concurrent` types**: `AtomicInteger`, `ConcurrentHashMap`, `CopyOnWriteArrayList`, `ReentrantLock`. Do not hand-roll locking with raw `synchronized` blocks unless you have a specific reason. Use `volatile` for single-variable visibility guarantees only.
4. **Python: understand the GIL's limits**: the GIL protects individual CPython object operations but not compound operations like `dict[k] = dict[k] + 1`. Use `threading.Lock` for compound read-modify-write. For `asyncio` code, use `asyncio.Lock`; even single-threaded async code has race conditions at `await` points.
5. **Prefer immutable data**: if a data structure is never mutated after creation, it is safe to share across all goroutines/threads without synchronization. Design data structures to be immutable by default; require explicit justification for mutation.
6. **Minimize shared state**: the safest shared variable is one that does not exist. Restructure concurrent code to use local variables and pass results via return values or channels. The more state is shared, the harder it is to reason about correctness.

## References
- Go Memory Model (go.dev/ref/mem) — formal specification of Go's synchronization guarantees
- "Java Concurrency in Practice" — Goetz et al. (the definitive Java concurrency reference)
- ThreadSanitizer (TSan) documentation — for C/C++/Go/Rust
- "The Art of Multiprocessor Programming" — Herlihy & Shavit
- TOCTOU (Time-of-check Time-of-use) vulnerability class — CWE-367
