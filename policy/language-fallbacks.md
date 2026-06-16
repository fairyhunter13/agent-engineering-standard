# Language Fallbacks

Use the repo's existing language and toolchain first.

- prefer the repo's primary language for new automation inside that repo
- use Python for cross-repo user-level integration scripts when no stronger local convention exists
- prefer stdlib over new dependencies
- if a verification tool is unavailable, state the limitation explicitly
