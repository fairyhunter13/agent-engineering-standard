---
name: internationalization
description: Architect multi-locale React/Next.js apps with proper i18n libraries, ICU pluralization, locale-aware formatting, and RTL layout support.
discipline: frontend
tags: [i18n, l10n, react-intl, next-i18next, accessibility]
---

# Internationalization

## When to use
Apply this skill when launching in multiple locales, when date/currency/number formatting varies by region, when RTL languages (Arabic, Hebrew, Persian, Urdu) are required, or when retroactively adding i18n to an app that was built English-only. Apply proactively during initial architecture — retrofitting is 5–10x more expensive.

## Signal
- Hardcoded English strings directly in JSX (`<h1>Welcome back</h1>`).
- `new Date().toLocaleDateString()` called without a locale argument.
- Currency formatted with string concatenation (`'$' + price.toFixed(2)`) instead of `Intl.NumberFormat`.
- Layout breaks or text overflows when switching to German (30% longer strings) or Arabic.
- `text-align: left` hardcoded in CSS instead of logical properties.
- No translation files — single language codebase with no extraction infrastructure.

## Why
i18n retrofitted after launch is expensive: every string must be found and extracted, every layout tested in RTL, every format audit checked for locale assumptions. Missing i18n excludes large markets — Arabic is the 5th most spoken language, German/French/Spanish collectively represent hundreds of millions of EU users. Regulatory requirements (EU public sector, some financial services) mandate localization.

## Remediate

1. **Choose an i18n library early.** For Next.js App Router: `next-intl` (recommended, RSC-compatible) or `next-i18next`. For non-Next.js React: `react-intl` (FormatJS). For lightweight needs: `i18next` + `react-i18next`.

2. **Set up locale routing in Next.js.** Configure the `i18n` key in `next.config.js` (Pages Router) or use `next-intl` middleware (App Router) to route `/en/dashboard`, `/ar/dashboard`, etc.:
   ```ts
   // middleware.ts (next-intl)
   import createMiddleware from 'next-intl/middleware';
   export default createMiddleware({
     locales: ['en', 'ar', 'de', 'fr'],
     defaultLocale: 'en',
   });
   ```

3. **Extract all user-visible strings to translation files.** Never hardcode display text in components. Use translation keys:
   ```tsx
   // Bad
   <h1>Welcome back, {name}!</h1>
   // Good
   const t = useTranslations('Dashboard');
   <h1>{t('welcome', { name })}</h1>
   ```
   Translation files live in `messages/en.json`, `messages/ar.json`, etc.

4. **Use ICU message syntax for pluralization and interpolation.** Never use ternary operators for plurals — ICU handles all plural rules across languages:
   ```json
   {
     "itemCount": "{count, plural, =0 {No items} one {# item} other {# items}}"
   }
   ```
   Arabic has 6 plural forms; English has 2; ICU handles both with the same message format.

5. **Format numbers, dates, and currencies with `Intl`.** Never hand-format:
   ```ts
   // Bad
   '$' + price.toFixed(2)
   // Good
   new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(price)

   // Bad
   new Date(ts).toLocaleDateString()
   // Good
   new Intl.DateTimeFormat(locale, { dateStyle: 'long' }).format(new Date(ts))
   ```
   `react-intl` / `next-intl` wrap these with locale-aware hooks: `useFormatter().number(price, { style: 'currency' })`.

6. **Support RTL layout.** When `locale` is Arabic, Hebrew, or Persian:
   - Set `dir="rtl"` on `<html>` (handle in your root layout).
   - Replace all directional CSS properties with logical equivalents:
     ```css
     /* Bad — directional */
     margin-left: 16px; padding-right: 8px; float: left;
     /* Good — logical */
     margin-inline-start: 16px; padding-inline-end: 8px; float: inline-start;
     ```
   - Use CSS `writing-mode` and `direction` to flip flex/grid layouts automatically.
   - Test with Arabic lorem ipsum text: "لوريم إيبسوم".

7. **Pseudo-localize during development.** Pseudo-localization replaces every character with an accented/extended version to reveal hardcoded strings and layout overflow without needing real translations:
   ```
   "Welcome" → "[Ŵēḷčōṁē]"
   ```
   Libraries: `pseudolocalization` npm package or Lingui's pseudo-locale.

8. **Lint for missing translation keys.** Use `eslint-plugin-i18n-json` or `i18next-parser` to extract keys used in code and compare against translation files. Missing keys should fail CI.

9. **Handle locale in server components.** In Next.js App Router, access locale from the `params` or `next-intl` headers — do not use `navigator.language` on the server:
   ```tsx
   export default async function Page({ params: { locale } }) {
     const messages = await import(`../messages/${locale}.json`);
     // ...
   }
   ```

## References
- next-intl documentation (next-intl.vercel.app)
- FormatJS / react-intl documentation (formatjs.io)
- ICU Message Format specification
- MDN — Intl API reference
- W3C Internationalization Activity (w3.org/International)
