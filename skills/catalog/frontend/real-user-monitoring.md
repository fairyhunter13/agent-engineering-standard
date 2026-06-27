---
name: real-user-monitoring
description: Instrument production apps with Real User Monitoring (RUM) to capture Core Web Vitals and performance metrics from actual users.
discipline: frontend
tags: [rum, performance, web-vitals, monitoring, analytics]
---

# Real User Monitoring (RUM)

## When to use
Apply this skill when Lighthouse/synthetic scores are green but users still complain about slowness; when there is no production performance data; when an A/B test may affect performance and you need to measure the impact; or when Core Web Vitals in Google Search Console are missing because there is insufficient field data.

## Signal
- Lighthouse score is green (90+) but users on slow networks or devices report sluggishness.
- No CWV data in Google Search Console ("Not enough data" status).
- Performance regressions discovered only after user complaints, not from monitoring.
- P99 performance unknown — only lab median scores available.
- No segmentation of performance by device class, geography, or connection type.
- No alerting when a deploy causes a performance regression.

## Why
Synthetic tests (Lighthouse, WebPageTest) run in controlled lab conditions — fast CPU, stable network, single run, no browser extensions, no third-party content. Real users have slower devices (2–4x slower CPU), variable networks (3G to 5G), browser extensions, and run across dozens of geographic regions. RUM captures the distribution of real experience, including P75 and P99 tail latencies where the worst user experiences hide. Google Search Console CWV data requires minimum 75 qualified page loads from real Chrome users — without RUM you cannot validate you are meeting that threshold.

## Remediate

1. **Add `web-vitals.js` to your application.** This is the official Google library that measures LCP, INP, CLS, FCP, and TTFB with the same methodology used by Chrome and CrUX:
   ```sh
   npm install web-vitals
   ```
   ```ts
   import { onLCP, onINP, onCLS, onFCP, onTTFB } from 'web-vitals';

   function sendToAnalytics({ name, value, id, delta, rating }: Metric) {
     fetch('/analytics', {
       method: 'POST',
       body: JSON.stringify({ name, value, id, delta, rating, url: location.href }),
       keepalive: true, // survives page unload
     });
   }

   onLCP(sendToAnalytics);
   onINP(sendToAnalytics);
   onCLS(sendToAnalytics);
   onFCP(sendToAnalytics);
   onTTFB(sendToAnalytics);
   ```

2. **Send metrics to your analytics or APM platform.** Options in order of ease of integration:
   - **Google Analytics 4** — `gtag('event', name, { value, metric_id: id })` then view in GA4 Explorations.
   - **Datadog RUM** — `@datadog/browser-rum` SDK includes web-vitals automatically.
   - **New Relic Browser** — automatic CWV collection.
   - **Custom backend** — send to your own endpoint and store in ClickHouse/BigQuery for custom dashboards.

3. **Segment by device, geography, and connection.** A P75 LCP of 2.3 s may be passing overall while mobile users in Southeast Asia see 5 s. Capture and store:
   ```ts
   {
     name: 'LCP',
     value: 2340,
     deviceType: navigator.userAgent.match(/Mobile/) ? 'mobile' : 'desktop',
     connection: (navigator as any).connection?.effectiveType ?? 'unknown',
     country: '', // injected by CDN edge or IP geolocation
     url: location.pathname,
   }
   ```

4. **Set performance budget alerts.** Configure your APM to alert when:
   - P75 LCP > 2.5 s
   - P75 INP > 200 ms
   - P75 CLS > 0.1
   Alert on a 15-minute rolling window after each deploy, and on a daily P75 baseline for trending.

5. **Track per-deploy performance.** Attach the Git commit SHA or deploy ID to each metric event. This allows you to compare P75 LCP before and after a deploy to detect regressions immediately. Many APM platforms have built-in deploy markers.

6. **Check Google CrUX (Chrome User Experience Report) monthly.** CrUX aggregates real Chrome user data for your domain and feeds Google Search Console. Check via:
   - Google Search Console → Core Web Vitals report.
   - CrUX API: `https://chromeuxreport.googleapis.com/v1/records:queryRecord`
   - PageSpeed Insights — shows both field data (CrUX) and lab data (Lighthouse) side by side.

7. **Run `lighthouse-ci` in CI as a synthetic floor.** Synthetic CI tests catch obvious regressions before they reach real users. Pair with RUM for the full picture:
   ```yaml
   # .github/workflows/ci.yml
   - name: Lighthouse CI
     run: npx lhci autorun
   ```
   Set `assert` budgets in `.lighthouserc.json` to fail PRs that regress below your thresholds.

8. **Correlate RUM with business metrics.** Track conversion rate alongside LCP in the same dashboard. A well-documented 2019 Google study found 1 s LCP improvement → 10%+ conversion improvement. Use this data to justify performance work to product stakeholders.

## References
- web-vitals.js library (GoogleChrome/web-vitals)
- Google Chrome User Experience Report (CrUX) API
- Datadog RUM documentation
- Lighthouse CI (GoogleChrome/lighthouse-ci)
- web.dev/articles/vitals-field-measurement-best-practices
