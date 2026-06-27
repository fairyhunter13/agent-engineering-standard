---
name: wcag-accessibility
description: Audit and remediate UI for WCAG 2.2 AA compliance, covering contrast, keyboard access, ARIA, and screen-reader correctness.
discipline: frontend
tags: [accessibility, wcag, a11y, html, aria]
---

# WCAG Accessibility

## When to use
Apply this skill when building or auditing any user-facing UI for legal compliance (ADA, EAA effective June 2025) or for inclusive UX. It is especially critical before any public launch, major redesign, or when an accessibility complaint is received.

## Signal
- `axe-core` or Lighthouse a11y score below 90.
- Images missing `alt` attributes or using empty `alt` on meaningful content.
- Color contrast ratio below 4.5:1 for body text or 3:1 for large text (18 pt / 14 pt bold).
- Keyboard navigation breaks: focus disappears, tab order is illogical, or modals do not trap focus.
- Interactive elements (buttons, links, custom widgets) have no accessible name.
- Form inputs lack associated `<label>` elements or `aria-labelledby`.
- JavaScript-driven state changes not announced to screen readers.

## Why
WCAG 2.2 AA is the legal baseline under the EU European Accessibility Act (EAA, enforced June 2025) and the US ADA (DOJ final rule March 2024). Non-compliance carries injunction and fine risk, and excludes approximately 15% of the global population who live with some form of disability. Accessibility retrofitted after launch costs 5–10x more to fix than building correctly from the start.

## Remediate

1. **Run automated audits first.** Execute `axe-core` via the browser extension or `jest-axe` in unit tests, and Lighthouse in CI (`--only-categories=accessibility`). Fix all automated violations — they represent ~30–40% of real issues with zero false-positive rate when the rule fires.

2. **Contrast ratios.** Check every text/background combination at `contrast-checker.org` or the browser DevTools accessibility panel. Body text must meet 4.5:1; large text (≥18 pt or ≥14 pt bold) must meet 3:1. Non-text UI components (icon borders, focus rings) need 3:1 against adjacent color.

3. **Images.** Every `<img>` must carry an `alt` attribute. Decorative images use `alt=""`. Informational images use concise descriptive text. Complex images (charts, diagrams) need a long description via `aria-describedby` pointing to a visible caption or a hidden `<div>`.

4. **Keyboard operability.** Every interactive element must be reachable via Tab and activated by Enter/Space. Never use `outline: none` without a visually distinct replacement focus indicator. Modal dialogs must trap focus inside themselves while open — implement a focus trap loop. Test entirely keyboard-only: no mouse, no trackpad.

5. **Focus management.** When a modal or drawer opens, move programmatic focus to its first interactive element (`dialog.querySelector('[autofocus], button, [href], input')`). When it closes, return focus to the trigger element. On SPA route changes, move focus to the page `<h1>`.

6. **Forms.** Every `<input>`, `<select>`, and `<textarea>` must have an associated `<label>` via explicit `for`/`id` pair or a wrapping `<label>`. Error messages must be linked to the offending input via `aria-describedby`. Required fields use `required` (HTML) or `aria-required="true"` (custom widgets).

7. **ARIA usage.** Prefer semantic HTML (`<button>`, `<nav>`, `<main>`, `<article>`, `<dialog>`) over ARIA roles. Add ARIA only to fill genuine gaps — incorrect ARIA is worse than no ARIA. Follow the ARIA Authoring Practices Guide patterns for tabs, comboboxes, and tree widgets.

8. **Live regions.** Dynamic content updates (toast notifications, loading spinners resolving, error summaries) must be announced via `aria-live="polite"` or `role="status"`. Use `aria-live="assertive"` only for time-critical errors.

9. **Screen-reader testing.** Test with NVDA + Firefox (Windows) and VoiceOver + Safari (macOS/iOS). Verify that custom widgets announce state (`aria-expanded`, `aria-selected`, `aria-checked`) and that landmark regions (`<main>`, `<nav>`, `<aside>`) are present and labeled.

10. **Reduced motion.** Wrap all animations in `@media (prefers-reduced-motion: reduce)` and remove or drastically slow them. This is WCAG 2.3.3 at AAA level but is expected practice and often required by enterprise customers.

## References
- WCAG 2.2 specification (W3C, October 2023)
- ARIA Authoring Practices Guide (W3C APG)
- EU European Accessibility Act (EAA 2019/882)
- US DOJ ADA Web Accessibility Guidance (March 2024)
- axe-core / jest-axe libraries (Deque Systems)
