---
name: code-splitting-and-lazy-loading
description: Split JS bundles by route and component to defer loading of code until it is actually needed, improving Time to Interactive.
discipline: frontend
tags: [performance, code-splitting, webpack, react, lazy-loading]
---

# Code Splitting and Lazy Loading

## When to use
Apply this skill when all routes share a single large JS bundle, when heavy dependencies (chart libraries, rich text editors, PDF viewers) load at startup regardless of whether the user visits their page, or when First Load JS in the Next.js build output grows with each feature added.

## Signal
- Next.js build output shows First Load JS > 250 KB for any route.
- Webpack/Vite bundle analysis shows chart libraries (Recharts, Chart.js, D3), editors (TipTap, Quill), or map SDKs in the main entry chunk.
- All routes bundled into a single file with no async chunks.
- A modal or drawer's entire component tree (including dependencies) loads on page startup.
- Time to Interactive regresses each sprint as features are added.

## Why
Loading all code at startup means the user's browser must download, parse, and compile JavaScript for features they may never visit. On a mid-range mobile device on 4G, each 100 KB of additional initial JS can add 300–500 ms of processing time. Code splitting defers loading until the user navigates to a route or triggers the relevant interaction, improving initial load without sacrificing feature richness.

## Remediate

1. **Route-level code splitting.** In React (non-Next.js), lazy-load every route:
   ```tsx
   import React, { lazy, Suspense } from 'react';
   const CheckoutPage = lazy(() => import('./pages/Checkout'));
   const DashboardPage = lazy(() => import('./pages/Dashboard'));

   function App() {
     return (
       <Suspense fallback={<PageSkeleton />}>
         <Routes>
           <Route path="/checkout" element={<CheckoutPage />} />
           <Route path="/dashboard" element={<DashboardPage />} />
         </Routes>
       </Suspense>
     );
   }
   ```
   In Next.js App Router, every `page.tsx` is automatically a separate chunk — no extra work required.

2. **Component-level splitting for heavy off-screen UI.** Lazy-load modals, drawers, full-screen dialogs, and heavy widgets that are not visible on initial page load:
   ```tsx
   const RichTextEditor = lazy(() => import('./RichTextEditor'));
   const ChartPanel = lazy(() => import('./ChartPanel'));

   function ReportPage() {
     const [showEditor, setShowEditor] = useState(false);
     return (
       <>
         <button onClick={() => setShowEditor(true)}>Edit</button>
         {showEditor && (
           <Suspense fallback={<EditorSkeleton />}>
             <RichTextEditor />
           </Suspense>
         )}
       </>
     );
   }
   ```
   In Next.js, use `next/dynamic`:
   ```ts
   const RichTextEditor = dynamic(() => import('./RichTextEditor'), { ssr: false });
   ```

3. **Prefetch likely-next routes on hover.** Once the initial page loads, speculatively load the next likely route:
   ```tsx
   // Next.js — prefetch automatically on <Link> hover
   <Link href="/checkout" prefetch>Checkout</Link>
   // Vanilla React — prefetch on hover
   <a href="/checkout" onMouseEnter={() => import('./pages/Checkout')}>Checkout</a>
   // Programmatic in Next.js
   const router = useRouter();
   <button onMouseEnter={() => router.prefetch('/checkout')}>Checkout</button>
   ```

4. **Avoid over-splitting.** Each async chunk has HTTP overhead. Do not split below ~10 KB. More than 20 chunks for a single page causes HTTP/2 head-of-line issues. Use Webpack's `optimization.splitChunks.minSize: 10000` or Vite's `build.rollupOptions.output.manualChunks` to merge tiny chunks.

5. **Lazy-load third-party scripts.** Analytics, chat widgets, and A/B testing scripts should load after the page is interactive. Use `<Script strategy="lazyOnload">` in Next.js, or add `defer` / dynamic insertion in vanilla HTML.

6. **Validate split effectiveness.** After adding code splitting, run the bundle analyzer and verify:
   - The main bundle no longer includes the split component's imports.
   - Each new async chunk is > 10 KB (merges anything smaller).
   - First Load JS in Next.js build output is reduced for the affected routes.

7. **Handle Suspense fallbacks thoughtfully.** Suspense boundaries should show a meaningful skeleton that matches the layout of the loading content, not a full-page spinner. This prevents layout shift when content loads.

8. **Test on a throttled connection.** Open Chrome DevTools Network tab, set throttling to "Slow 4G", reload, and observe: the initial page should load and be interactive before any lazy-loaded chunks appear.

## References
- React documentation — Code-Splitting (react.dev)
- Next.js dynamic imports documentation
- web.dev/code-splitting-with-dynamic-imports-in-nextjs
- Webpack SplitChunksPlugin documentation
