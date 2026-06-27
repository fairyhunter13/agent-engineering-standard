---
name: debugging-methodology
description: Apply a systematic hypothesis-driven method to diagnose bugs faster and reach the correct root cause.
discipline: craft
tags: [debugging, bisect, reproduction, root-cause, methodology]
---

# Debugging Methodology

## When to use
Investigating a hard-to-reproduce bug; conducting a production incident root cause analysis; diagnosing a bug reported without a reliable reproduction case.
Apply this any time a debugging session exceeds 30 minutes without a confirmed hypothesis.

## Signal
- "It works on my machine" — the bug does not reproduce locally or in staging.
- The debugging approach is random-guessing: changing code and hoping the bug disappears.
- A debugging session has run for >2 hours without a written hypothesis.
- The fix is applied without understanding why the bug occurred — it might be treating a symptom.
- Adding logging to investigate causes the bug to disappear (heisenbug), suggesting a timing or resource dependency.
- Root cause is reported as "we deployed a fix" without documenting what specifically was wrong and why.

## Why
Unstructured debugging (also known as "random walk debugging") is slow because it explores a search space without pruning it.
Every change made without a hypothesis is a coin flip; you might get lucky, but you might also introduce new bugs while chasing the wrong root cause.
Systematic methodology — reproduce, narrow, hypothesize, test — reduces the search space at each step and converges on root cause reliably.
The value of finding the root cause (not just a symptom fix) is that you prevent the same class of bug from recurring elsewhere in the codebase.

## Remediate
1. **Reproduce first — do not touch code until you can**: a reliable, minimal reproduction is the most valuable asset in a debugging session. Without it, every hypothesis is unverifiable. Minimum viable reproduction: the smallest input, configuration, and environment that triggers the bug reliably. If you cannot reproduce it, reproduce the conditions (load, timing, data state) that correlate with the bug.
2. **Narrow scope with `git bisect`**: if the bug appeared recently, `git bisect start; git bisect bad; git bisect good <last-known-good-sha>` will find the introducing commit in O(log n) steps. This eliminates entire subsystems from consideration and often reveals the root cause just by reading the introducing commit.
3. **Formulate a written hypothesis before changing code**: "I believe the cache is returning stale data for user IDs created in the last 5 minutes because the TTL is set to 300 seconds but the session token expires in 240 seconds." A hypothesis is falsifiable: it predicts what you will observe if it is true. Write it down — the act of writing it exposes gaps.
4. **Change one variable at a time**: test the hypothesis by changing exactly one thing and observing the outcome. If you change three things and the bug disappears, you do not know which change fixed it. Binary search through the variable space.
5. **Read observability data before reading code**: check logs, metrics, and distributed traces for the time window around the bug. Production state is ground truth; code is your model of what should happen. If logs show a database query timing out, start there — not in the application business logic.
6. **Document the full investigation**: once resolved, write the root cause analysis: (a) what was the observable symptom, (b) what was the actual root cause, (c) how was it reproduced, (d) what was the fix, (e) what follow-up work prevents recurrence. Put this in the commit message or PR description. Future engineers (and your future self) will thank you when a similar bug appears.

## References
- "The Pragmatic Programmer" — Hunt & Thomas, Chapter: "Debugging"
- `git bisect` documentation (git-scm.com/docs/git-bisect)
- "Debugging: The 9 Indispensable Rules for Finding Even the Most Elusive Software and Hardware Problems" — David Agans
- SRE Book (Google): Chapter 12 — Effective Troubleshooting
- "Why Programs Fail: A Guide to Systematic Debugging" — Andreas Zeller
