---
name: core-web-vitals
description: Diagnose and improve Google Core Web Vitals (LCP, INP, CLS) using RUM data and targeted optimization techniques.
discipline: frontend
tags: [performance, lcp, inp, cls, rum, web-vitals]
---

# Core Web Vitals

## When to use
Apply this skill when Google Search ranking is affected by Core Web Vitals scores, when users report perceived slowness or layout instability, or when PageSpeed Insights flags yellow/red metrics. Also apply proactively before major releases to prevent regressions.

## Signal
- Lighthouse CWV score yellow (needs improvement) or red (poor) in any metric.
- LCP (Largest Contentful Paint) > 2.5 s in field data.
- INP (Interaction to Next Paint) > 200 ms in field data.
- CLS (Cumulative Layout Shift) > 0.1 in field data.
- Google Search Console Core Web Vitals report shows URLs in "Poor" or "Needs Improvement" groups.
- `web-vitals.js` RUM data shows P75 or P90 exceeding thresholds.

## Why
Core Web Vitals (LCP, INP, CLS) are Google ranking signals as of 2021–2024 and measure real user experience. INP replaced FID (First Input Delay) in March 2024, raising the bar for responsiveness. A page failing CWV thresholds loses ranking positions and demonstrates actual user-experience problems — slow perceived load, janky interactions, and unstable layout that causes mis-taps.

## Remediate

### LCP (Largest Contentful Paint — target ≤ 2.5 s)

1. **Identify the LCP element** in Chrome DevTools Performance panel or PageSpeed Insights. It is usually a hero image, `<h1>`, or above-fold block.

2. **Preload the LCP resource.** Add `<link rel="preload" as="image" href="/hero.webp" fetchpriority="high">` in `<head>`. Remove any lazy-loading on the LCP image — never apply `loading="lazy"` to the LCP element.

3. **Serve from a CDN.** Reduce TTFB by serving static assets from a geographically close edge node. TTFB should be < 600 ms.

4. **Serve in modern formats.** WebP is 25–35% smaller than JPEG; AVIF is 50% smaller. Use `<picture>` with `<source type="image/avif">` fallback to WebP.

5. **Eliminate render-blocking resources.** Defer non-critical JS (`defer` / `async`). Inline critical CSS (above-fold styles) and load the rest asynchronously.

### INP (Interaction to Next Paint — target ≤ 200 ms)

6. **Find slow interactions** with Chrome DevTools Performance > Interactions panel or `PerformanceObserver` with `type: 'event'`.

7. **Yield to the browser between tasks.** Long tasks (> 50 ms) block the main thread. Break them up with `scheduler.yield()` (Chrome 115+) or `setTimeout(fn, 0)`. In React, use `startTransition` to defer non-urgent state updates.

8. **Reduce JS execution.** Remove unused code. Avoid synchronous operations (layout reads, forced reflows) inside event handlers. Cache DOM lookups.

9. **Debounce/throttle high-frequency events** (scroll, resize, input) but keep click/keydown handlers instant — users expect immediate visual feedback.

### CLS (Cumulative Layout Shift — target ≤ 0.1)

10. **Set explicit dimensions on every image and embed.** Always specify `width` and `height` attributes. Use CSS `aspect-ratio` when exact dimensions are unknown.

11. **Reserve space for dynamic content.** Banners, ads, and late-loading widgets that insert above existing content cause CLS. Reserve their space in the initial layout with `min-height`.

12. **Avoid inserting content above the fold** after load. If a cookie banner or notification bar must appear, push content down from the start or overlay it without reflowing the page.

13. **Web fonts.** Use `font-display: optional` or `font-display: swap` with `<link rel="preload">` for fonts used in LCP text to prevent layout shifts from font swaps.

### Measurement

14. **Instrument with `web-vitals.js`** in production:
    ```js
    import { onLCP, onINP, onCLS } from 'web-vitals';
    onLCP(sendToAnalytics);
    onINP(sendToAnalytics);
    onCLS(sendToAnalytics);
    ```
    Field data is the ground truth — lab scores (Lighthouse) are directional only.

15. **Check CrUX monthly** via Google Search Console or the CrUX API to track percentile improvements across real users segmented by device type.

## References
- Google Core Web Vitals documentation (web.dev/vitals)
- web-vitals.js library (GoogleChrome/web-vitals)
- Chrome User Experience Report (CrUX)
- `scheduler.yield()` proposal (WICG)
