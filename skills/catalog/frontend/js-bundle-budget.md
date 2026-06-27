---
name: js-bundle-budget
description: Enforce JavaScript bundle size budgets to keep Time to Interactive fast on mid-range mobile devices.
discipline: frontend
tags: [performance, bundle, webpack, vite, javascript]
---

# JS Bundle Budget

## When to use
Apply this skill when the JS bundle size has grown without an enforcement gate, when Time to Interactive (TTI) is slow on mobile, or when a Lighthouse audit shows JS parse/compile time exceeding 1 second. Also apply when onboarding a new feature that pulls in a heavy dependency.

## Signal
- Main JS bundle exceeds 400 KB gzipped.
- Webpack Bundle Analyzer or `rollup-plugin-visualizer` shows large, unused dependencies.
- Lighthouse "Reduce unused JavaScript" warning.
- `lighthouse --preset=mobile` shows JS parse + compile > 1 s.
- No bundle size check in CI — size grows undetected with each PR.
- `import moment from 'moment'` (moment.js alone is ~67 KB gzipped).

## Why
Large JS bundles directly delay Time to Interactive, especially on mid-range mobile devices (Moto G Power class), which parse and compile JavaScript 2–4x slower than a MacBook Pro. Users on 4G with slow devices experience blank screens during JS parsing even though the HTML has arrived. Every 100 KB of gzipped JS adds roughly 300–400 ms of CPU time on a mid-range phone.

## Remediate

1. **Set a bundle budget and enforce it in CI.** The June 2026 standard is ≤ 400 KB gzipped total initial JS. Use the `size-limit` npm package:
   ```json
   // package.json
   "size-limit": [
     { "path": "dist/main.js", "limit": "400 KB", "gzip": true }
   ]
   ```
   Run `npx size-limit` in CI and fail the build on violation.

2. **Analyze what is large.** For Webpack: `npx webpack-bundle-analyzer dist/stats.json`. For Vite: add `rollup-plugin-visualizer` to `vite.config.ts` and open the generated `stats.html`. Look for: large deps duplicated across chunks, full library imports where only one function is used, polyfills included for modern browsers.

3. **Code-split by route.** Every route should be a separate async chunk:
   ```tsx
   // React
   const CheckoutPage = React.lazy(() => import('./pages/Checkout'));
   // Next.js does this automatically per page/app-router segment
   ```
   The initial bundle should load only what is needed for the landing route.

4. **Replace heavy dependencies.**
   - `moment` (67 KB) → `date-fns` (named imports, tree-shakeable) or native `Intl.DateTimeFormat`.
   - `lodash` (full import, 24 KB) → `lodash-es` named imports or native equivalents.
   - `axios` → native `fetch` (zero KB).
   - `yup` → `zod` (smaller + better TypeScript inference).
   - Heavy icon packs: import individual icons, not the full set.

5. **Tree-shake correctly.** Import named exports only:
   ```ts
   // Bad — imports everything
   import _ from 'lodash';
   // Good — imports only debounce
   import { debounce } from 'lodash-es';
   ```
   Ensure `"sideEffects": false` is set in `package.json` for your own packages.

6. **Audit polyfills.** Target modern browsers (ES2020+ baseline). Remove `core-js` polyfills for features already native in your browser support matrix. Use `@babel/preset-env` with a `targets` config that matches your actual browser support policy.

7. **Lazy-load below-fold components.** Rich text editors (Quill, TipTap), chart libraries (Chart.js, Recharts), PDF viewers, and map SDKs should never be in the initial bundle. Wrap them in `React.lazy()` with a `<Suspense fallback>`.

8. **Avoid chunk fragmentation.** More than ~20 chunks causes HTTP/2 multiplexing overhead. Each chunk should be at least 10 KB. Tune Webpack's `optimization.splitChunks.minSize` or Vite's `build.rollupOptions.output.manualChunks` to merge tiny chunks.

9. **Monitor continuously.** Add `bundlesize` or `size-limit` as a required CI check so that every PR that exceeds the budget requires deliberate override. Include bundle size in your PR description template to make it visible.

## References
- `size-limit` (ai/size-limit on GitHub)
- `rollup-plugin-visualizer` (btd/rollup-plugin-visualizer)
- webpack-bundle-analyzer
- web.dev/reduce-javascript-payloads-with-code-splitting
