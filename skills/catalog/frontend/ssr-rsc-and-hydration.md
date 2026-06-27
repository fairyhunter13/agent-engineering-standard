---
name: ssr-rsc-and-hydration
description: Correctly architect Next.js apps with React Server Components, avoid hydration mismatches, and choose the right rendering strategy per route.
discipline: frontend
tags: [nextjs, react, ssr, rsc, hydration, performance]
---

# SSR, RSC, and Hydration

## When to use
Apply this skill when building with Next.js App Router (RSC) or any React SSR setup; when debugging hydration mismatch errors; when choosing between SSG, SSR, ISR, and RSC strategies; or when client-side bundles are larger than expected because server-only data is leaking into the client.

## Signal
- React console error: "Hydration failed because the initial UI does not match what was rendered on the server."
- `use client` directive added to components that do not need browser APIs or interactivity.
- Database queries or secrets visible in the browser bundle (`window.__NEXT_DATA__` contains sensitive fields).
- Route performance worse than expected after migrating to RSC.
- Components that render differently on server vs. client (e.g., using `typeof window !== 'undefined'` in render).

## Why
React Server Components (RSC) keep data-fetching and heavy computation on the server, eliminating the need to ship that code and its dependencies to the client. The client bundle shrinks, pages load faster, and sensitive operations (DB access, secret usage) stay server-side. Hydration mismatches occur when the server-rendered HTML differs from what React would render on the client — React throws away the server HTML and re-renders, causing a layout flash and wasted work.

## Remediate

1. **Default to React Server Components.** In Next.js App Router, every component is a Server Component by default. Only add `"use client"` when the component requires:
   - Browser APIs (`window`, `document`, `localStorage`, geolocation).
   - React hooks with interactivity (`useState`, `useEffect`, `useRef`, custom hooks wrapping these).
   - Event handlers that run in the browser (`onClick`, `onChange`).

2. **Keep the client boundary as deep as possible.** If a large component tree only needs one interactive leaf, mark only the leaf as `"use client"` — not the parent. Server Components can still render inside Client Component trees when passed as `children` props.

3. **Guard server-only imports.** Install the `server-only` package and import it at the top of any module that contains DB queries, secrets, or server-side business logic:
   ```ts
   import 'server-only';
   ```
   This causes a build error if the module is accidentally imported into a Client Component.

4. **Fix hydration mismatches.** Common causes:
   - `Date.now()`, `Math.random()`, or `new Date()` called directly in render — move to a `useEffect` or pass as props from the server.
   - `typeof window !== 'undefined'` branches in render — use `useEffect` for client-only rendering.
   - Browser extensions that modify the DOM before React hydrates — usually harmless but causes console warnings; suppress with `suppressHydrationWarning` only on the specific element.
   - Locale-dependent formatting (numbers, dates) that differs between server locale and client locale — always pass explicit locale strings.

5. **Choose the right rendering strategy per route.**
   - **RSC (Server Components)** — default for all data-fetching pages. Renders on every request or with Next.js caching.
   - **Static (SSG / `generateStaticParams`)** — fully static content that never changes or changes on a schedule (marketing pages, blog posts). Fastest TTFB.
   - **SSR (`dynamic = 'force-dynamic'`)** — fully personalized content (dashboards, user-specific pages) that must be fresh on every request.
   - **ISR (`revalidate = N`)** — mostly static content that updates periodically (product listings, news). Best balance of performance and freshness.

6. **Data fetching in Server Components.** Fetch directly in `async` Server Components — no need for `useEffect` or React Query for server data:
   ```tsx
   async function ProductPage({ id }: { id: string }) {
     const product = await db.products.findUnique({ where: { id } });
     return <ProductDetail product={product} />;
   }
   ```
   Use React's `cache()` to deduplicate fetches called from multiple components in the same render.

7. **Measure hydration time.** Use `reportWebVitals` in `next/app` and track the "hydration" metric. A hydration time above 200 ms on a mid-range mobile device indicates too much JavaScript is being sent to the client.

8. **Streaming with Suspense.** Wrap slow data-fetching Server Components in `<Suspense fallback={<Skeleton />}>` to stream partial HTML — the shell renders instantly while data loads:
   ```tsx
   <Suspense fallback={<ProductSkeleton />}>
     <SlowProductReviews productId={id} />
   </Suspense>
   ```

## References
- Next.js App Router documentation (nextjs.org/docs/app)
- React Server Components RFC (github.com/reactjs/rfcs)
- `server-only` npm package
- web.dev/articles/react-server-components
