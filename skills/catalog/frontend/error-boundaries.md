---
name: error-boundaries
description: Isolate React component crashes with error boundaries to prevent white screen of death and enable graceful partial-page degradation.
discipline: frontend
tags: [react, error-handling, resilience, ux]
---

# Error Boundaries

## When to use
Apply this skill when any unhandled JS error in a React component takes down the entire page (white screen of death); when building dashboards or portals where widgets should fail independently; or when integrating third-party components that may throw unpredictably.

## Signal
- Console shows an unhandled React error and the entire page goes blank.
- No fallback UI shown to users on component failure — just an empty white or grey screen.
- Third-party widget errors cascade into the whole application crashing.
- Error monitoring (Sentry, Bugsnag) has no records of caught React errors — they are being silently swallowed or appear only as uncaught exceptions.
- `componentDidCatch` is absent from the codebase.

## Why
Without error boundaries, any thrown error inside a React component causes the entire React tree to unmount. This is intentional by design — React cannot know the extent of corrupted state. Error boundaries are React's mechanism for containing this failure to a subtree, rendering a fallback UI, and keeping the rest of the page functional. Without them, a bug in a sidebar widget destroys the entire application for the user.

## Remediate

1. **Install `react-error-boundary`.** This library provides a production-ready, well-maintained `<ErrorBoundary>` component that avoids the boilerplate of writing a class component:
   ```sh
   npm install react-error-boundary
   ```

2. **Wrap each independently-failing section.** Identify the major independent sections of your UI: header, sidebar, main content area, each widget on a dashboard, each panel. Wrap each with an `<ErrorBoundary>`:
   ```tsx
   import { ErrorBoundary } from 'react-error-boundary';

   function Dashboard() {
     return (
       <div>
         <ErrorBoundary FallbackComponent={WidgetError}>
           <RevenueChart />
         </ErrorBoundary>
         <ErrorBoundary FallbackComponent={WidgetError}>
           <RecentOrders />
         </ErrorBoundary>
       </div>
     );
   }
   ```

3. **Write a meaningful fallback component.** The fallback should tell the user something went wrong and offer a recovery action:
   ```tsx
   function WidgetError({ error, resetErrorBoundary }: FallbackProps) {
     return (
       <div role="alert" className="error-widget">
         <p>This section failed to load.</p>
         <button onClick={resetErrorBoundary}>Try again</button>
       </div>
     );
   }
   ```
   The `resetErrorBoundary` callback clears the error state and re-renders the children from scratch.

4. **Log to error tracking inside `onError`.** Pass an `onError` callback to the `<ErrorBoundary>` to report errors to your observability platform:
   ```tsx
   <ErrorBoundary
     FallbackComponent={WidgetError}
     onError={(error, info) => {
       Sentry.captureException(error, { extra: { componentStack: info.componentStack } });
     }}
   >
     <RevenueChart />
   </ErrorBoundary>
   ```

5. **Place boundaries at the right granularity.** Too coarse (one boundary for the whole app) means a single failure still takes down most of the UI. Too fine (every leaf component) adds overhead and complexity with minimal benefit. A good heuristic: one boundary per independently useful unit of the page — each "card", "panel", or "section" that has standalone value.

6. **Add a top-level boundary as a last resort.** Even with granular boundaries, place one at the app root to catch anything that slips through:
   ```tsx
   // app/layout.tsx (Next.js App Router) or index.tsx
   <ErrorBoundary FallbackComponent={AppCrashFallback}>
     <App />
   </ErrorBoundary>
   ```
   The `AppCrashFallback` should offer a "Reload page" button.

7. **Error boundaries do NOT catch async errors.** `useEffect` errors, rejected Promises, and event-handler errors are not caught by class-component `componentDidCatch`. For those, use a global `window.addEventListener('unhandledrejection', ...)` and wrap async calls with `try/catch`. React 19's `use()` hook for Promises allows Suspense boundaries to catch async throws.

8. **Test error boundaries deliberately.** In development, throw intentionally in a component to verify the fallback renders and the error reaches your monitoring:
   ```tsx
   function BuggyComponent() {
     if (process.env.NODE_ENV === 'development' && triggerError) {
       throw new Error('Test error boundary');
     }
     return <div>Normal content</div>;
   }
   ```

## References
- React documentation — Error Boundaries (react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)
- react-error-boundary library (bvaughn/react-error-boundary)
- Sentry React SDK documentation
