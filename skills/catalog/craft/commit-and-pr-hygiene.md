---
name: commit-and-pr-hygiene
description: Write atomic, descriptive commits and focused PRs that make history searchable and bisect reliable.
discipline: craft
tags: [git, commits, pull-requests, changelog, conventional-commits]
---

# Commit and PR Hygiene

## When to use
Writing a commit message; opening a pull request; preparing a release and changelog; trying to bisect a regression.
Apply this as a standing practice on every commit and PR — hygiene degrades quickly when treated as optional.

## Signal
- Commit history is full of: "fix stuff", "WIP", "updates", "asdfg", "trying this", "final", "final2".
- One commit represents a week of work across five unrelated concerns — impossible to bisect or revert atomically.
- A PR contains 2,000 lines of diff with a description that says "refactored some things."
- `git bisect` identifies the introducing commit as a large unrelated change, making root cause analysis impossible.
- The CHANGELOG is written manually from memory at release time, missing half the changes.
- A release must be rolled back, but the "fix" commit is entangled with unrelated feature code that cannot be excluded.

## Why
Git history is the permanent record of every decision made in the codebase.
Good commits serve three future use cases simultaneously: (a) **bisect** — `git bisect` needs each commit to represent one logical change so that finding the introducing commit also identifies the root cause; (b) **revert** — atomic commits can be reverted safely; an entangled commit cannot be reverted without collateral damage; (c) **archaeology** — a commit message that explains *why* answers the question future maintainers will ask when they read the code.
A well-structured PR makes the reviewer's job tractable: they can understand the intent, verify the implementation matches, and approve with confidence.

## Remediate
1. **Follow Conventional Commits** for every commit message: `<type>(<scope>): <subject>`. Type is one of: `feat` (new feature), `fix` (bug fix), `refactor` (structural change, no behavior change), `test` (tests only), `docs`, `chore` (build/tooling), `perf`. Example: `fix(auth): prevent token leak on session timeout`. This schema enables automated changelog generation and clear commit classification.
2. **Atomic commits — one logical change per commit**: a commit should do exactly one thing. "Add cursor pagination to the orders API" is atomic. "Add cursor pagination + fix a null pointer + update dependencies" is not. Keep tests green at every commit — if you cannot, the commit is not complete.
3. **Commit message body explains the why, not the what**: the diff shows *what* changed; the message body explains *why* this change was necessary, what alternatives were considered, and what the tradeoffs are. Format: imperative mood subject line ≤72 characters; blank line; body paragraphs; optional `Closes #123` trailer.
4. **PR size ≤400 lines of meaningful diff**: PRs larger than this are reviewed poorly — reviewers lose focus, context, and the ability to hold the change in their head. If a feature requires more, decompose it into a stack: `1/3 add repository layer`, `2/3 add service layer`, `3/3 add HTTP handler`. Each PR in the stack should be independently reviewable and mergeable.
5. **PR description must answer three questions**: (a) *What* changed — one-paragraph summary of the change. (b) *Why* — the motivation: user story, bug, technical debt. (c) *How to test* — a concrete checklist of steps to verify correctness. Link to the issue or ticket. Screenshots for UI changes.
6. **Squash WIP commits before merge; preserve logical separation after squash**: during development, commit freely. Before merging, squash or reorganize WIP commits into a clean logical sequence using interactive rebase (`git rebase -i`). The merged history should read as a clear narrative, not a development diary. Tag releases with semantic versioning (`v1.4.2`); generate the CHANGELOG from Conventional Commit history using `conventional-changelog` or `git-cliff`.

## References
- Conventional Commits specification (conventionalcommits.org)
- "How to Write a Git Commit Message" — Chris Beams (cbea.ms/git-commit)
- Semantic Versioning (semver.org)
- `git bisect` documentation (git-scm.com/docs/git-bisect)
- `git-cliff` changelog generator (git-cliff.org)
- "My Favourite Git Commit" — David Thompson (dhwthompson.com)
