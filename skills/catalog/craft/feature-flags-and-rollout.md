---
name: feature-flags-and-rollout
description: Decouple deploy from release using feature flags to enable incremental rollout and instant kill-switch.
discipline: craft
tags: [feature-flags, rollout, deployment, launchdarkly, experimentation]
---

# Feature Flags and Rollout

## When to use
Releasing a risky or large feature to production without exposing it to all users simultaneously; running A/B experiments on new functionality; enabling trunk-based development without long-lived feature branches.
Apply this for any feature whose correctness or performance is uncertain at scale, or whose rollback must be faster than a redeploy.

## Signal
- New features ship all-or-nothing: either all users see it or none do, with no intermediate state.
- A bad deploy requires a hotfix and a new release cycle to revert — the rollback time is measured in hours, not seconds.
- Long-lived feature branches (`feature/new-checkout`) exist for weeks or months, accumulating merge conflicts.
- There is no way to disable a buggy feature post-deploy without reverting the entire release.
- A/B testing requires a separate deployment pipeline or a hard-coded percentage in application config.
- Beta users must be on a separate deployment environment rather than seeing a flag-gated code path.

## Why
Feature flags decouple two concerns that are often conflated: **deploy** (the code is in production) and **release** (users can see and use the feature).
Separating these allows code to be merged and deployed to production continuously while releases are controlled independently, eliminating long-lived branches and enabling trunk-based development.
The kill-switch property alone justifies the investment: turning off a broken feature takes seconds via a flag toggle, versus 15–45 minutes for a redeploy with approval gates.
Percentage rollouts allow catching problems at 1% traffic before they affect all users.

## Remediate
1. **Use a feature flag platform**: do not implement flags as environment variables or config files managed by hand. Use LaunchDarkly, Unleash (self-hosted), Flagsmith, or GrowthBook (open source, A/B-focused). These provide a UI, audit log, targeting rules, and SDKs for every language.
2. **Choose the right flag type for the use case**:
   - **Kill switch** (`on/off`): for emergency disable of any feature in production.
   - **Percentage rollout**: expose to 1% → 5% → 25% → 100% with a delay between steps to observe error rates.
   - **User targeting**: expose to `beta_users` group, specific user IDs, or users matching attribute rules (country, plan tier).
   - **Experiment (A/B)**: randomly split traffic; measure conversion rate, latency, or business metric difference between variants.
3. **Keep flag logic thin**: `if (flags.isEnabled("new-checkout", user)) { return newCheckout(cart) } return legacyCheckout(cart)`. No complex business logic inside the flag evaluation block. The flag is a routing decision, not a feature implementation.
4. **Safe default = off**: new flags should default to `false` (feature hidden). The default must represent the safe, currently-correct behavior. A flag defaulting to `true` means a flag service outage silently enables the new behavior for all users.
5. **Flag retirement is mandatory**: every flag must have an assigned owner and a removal target date set at creation time. After a flag is 100% rolled out and stable for ≥2 weeks, remove it from the codebase. Stale flags accumulate: 50 stale flags make the code unreadable and create a maintenance and audit burden. Run a quarterly flag audit.
6. **Log flag evaluations for audit**: log which flag variant each request was assigned to, correlated with request ID. This enables post-hoc analysis ("did the incident affect only users on the new variant?") and is required for A/B experiment analysis.

## References
- "Feature Toggles (aka Feature Flags)" — Martin Fowler (martinfowler.com)
- LaunchDarkly documentation: Flag types and targeting rules
- Unleash documentation: Activation strategies
- Pete Hodgson: "Feature Flags" on Martin Fowler's blog — flag taxonomy
- Trunk-Based Development (trunkbaseddevelopment.com) — feature flags as enabler
