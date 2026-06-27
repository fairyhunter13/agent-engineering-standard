---
name: code-review-discipline
description: Make code reviews fast, effective, and psychologically safe by distinguishing blocking issues from suggestions.
discipline: craft
tags: [code-review, collaboration, quality, feedback, pull-requests]
---

# Code Review Discipline

## When to use
Performing a code review as a reviewer; receiving review feedback as an author; establishing or auditing code review norms for a team.
Apply this any time a code review process is causing friction, taking too long, or missing real bugs.

## Signal
- Reviews routinely take >24 hours, blocking authors and creating batching pressure to merge untested code.
- Feedback is vague: "this could be cleaner," "I'm not sure about this approach," with no specific suggestion.
- Reviewers approve without actually verifying correctness — rubber-stamping to clear the queue.
- Review comments are indistinguishable between blocking correctness issues and stylistic preferences, forcing authors to guess which to act on.
- Authors feel personally criticized rather than receiving feedback on the code.
- PRs with architectural disagreements sit unresolved for days because the team avoids synchronous discussion.

## Why
A review process that is too slow, too vague, or too painful gets gamed — authors bypass it or reviewers rubber-stamp.
Both failure modes eliminate the actual value: catching bugs before they reach production, sharing knowledge across the team, and maintaining collective code ownership.
The key insight is that not all review comments are equal: conflating a blocking security vulnerability with a variable naming nit creates a false equivalence that makes it unclear what the author must do to ship.
Reviews that feel like attacks on the author's competence rather than examination of the code destroy psychological safety and reduce the quality of the code that gets submitted for review.

## Remediate
**Reviewer responsibilities:**
1. **Read the PR description and linked issue first**: understand the intent before reading code. Verify the implementation matches the stated intent. A PR that correctly implements the wrong solution is a failure — catch this at the description level, not line by line.
2. **Use a clear comment taxonomy**: prefix comments to communicate priority. `BLOCKING:` — correctness bug, security issue, API contract breakage, data loss risk — must be resolved before merge. `NIT:` or `SUGGESTION:` — style, naming, minor improvement — author's discretion. Unlabeled comments should be rare; clarifying questions are not blocking.
3. **Approve when your blocking concerns are addressed**, not when the code is perfect. The goal of review is to catch serious problems, not to redesign the solution. If the code is correct, safe, and maintainable, approve it even if you would have made different stylistic choices.
4. **Respond within 4 business hours**: long wait times for first review kill developer flow. If you cannot review within 4 hours, say so and suggest an alternative reviewer. Review latency is a team metric, not an individual one.

**Author responsibilities:**
5. **Keep PRs small (≤400 lines of meaningful diff)**: large PRs are reviewed poorly. If a change requires >400 lines, decompose it into a stack of smaller PRs with a clear dependency order. A PR description should make the reviewer's job easier, not harder.
6. **Self-review before requesting**: read your own diff in the PR UI before assigning reviewers. Catch your own typos, debug artifacts, commented-out code, and TODOs. Do not make reviewers find things you would catch yourself in 5 minutes.
7. **Respond to every comment**: even if you disagree, acknowledge the comment. `Agreed, fixed in abc123` or `I kept the original approach because X — let me know if you'd like to discuss further` is sufficient. Silent dismissal breaks trust.
8. **Call for synchronous discussion on architecture disagreements**: if a comment thread exceeds 4 exchanges without resolution, propose a 15-minute call. Architecture disagreements are not efficiently resolved in asynchronous text.

## References
- "Code Review Best Practices" — Ron Jeffries
- Google Engineering Practices: Code Review (google.github.io/eng-practices)
- "Conventional Comments" specification (conventionalcomments.org) — comment taxonomy
- "How to Make Your Code Reviewer Fall in Love with You" — Michael Lynch
- "The Art of the Code Review" — Sarah Mei
