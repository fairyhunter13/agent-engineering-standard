---
name: state-management-boundaries
description: Place React state at the correct layer (local, context, server, global) to eliminate prop drilling and unnecessary re-renders.
discipline: frontend
tags: [react, state, redux, zustand, architecture]
---

# State Management Boundaries

## When to use
Apply this skill when component trees suffer prop drilling deeper than 3 levels, when global state changes trigger re-renders across unrelated components, or when choosing between `useState`, React Context, Zustand, Redux Toolkit, and React Query for a new feature.

## Signal
- Props passed through 3+ intermediate components that do not use them ("prop drilling").
- Unrelated components re-render when a piece of state changes (visible in React DevTools Profiler with "Highlight updates").
- Server-fetched data stored in Redux/Zustand alongside local UI state.
- `useContext` on a large context object causing full tree re-renders on any change.
- `useEffect` with `fetch` calls duplicated across multiple components for the same data.
- Performance profiler shows "wasted renders" on components with identical props.

## Why
Incorrect state placement has two failure modes: (1) prop drilling — state too local, passed manually down many levels, becoming brittle to refactor; (2) over-broad global state — state too global, causing unnecessary re-renders and coupling unrelated components. Each category of state has a natural home; mixing them creates both problems simultaneously.

## Remediate

1. **Classify state before placing it.** Ask three questions: Is this data from the server? Is this shared across distant components? Is this ephemeral UI state? The answer determines the right tool.

2. **Server state → React Query or SWR.** Any data fetched from an API is server state. Do not put it in Redux or Zustand. Use `@tanstack/react-query` (React Query) or `swr`:
   ```ts
   const { data: user, isLoading } = useQuery({
     queryKey: ['user', userId],
     queryFn: () => fetchUser(userId),
   });
   ```
   React Query handles caching, background refetch, deduplication, loading/error states — things Redux requires manual wiring for.

3. **Local UI state → `useState` / `useReducer`.** Toggle state (open/closed), form input values, selected tab, and hover state belong in the component that owns the UI element. Do not lift this to global state.

4. **Shared local state → lift to nearest common ancestor.** When two sibling components share state, lift it to their parent. This is the correct solution up to ~3 levels.

5. **Deep shared UI state → Zustand (preferred) or Redux Toolkit.** When state genuinely needs to cross major component boundaries (theme, user preferences, shopping cart, notification queue), use a lightweight store:
   ```ts
   // Zustand
   const useCartStore = create<CartStore>((set) => ({
     items: [],
     addItem: (item) => set((s) => ({ items: [...s.items, item] })),
   }));
   ```
   Reserve Redux Toolkit for teams already using it or for large-scale apps requiring Redux DevTools time-travel.

6. **Avoid over-broad React Context.** A single `<AppContext.Provider value={{ user, theme, notifications, cart }}>` causes every consumer to re-render when any field changes. Split contexts by domain (UserContext, ThemeContext, CartContext) and use `useMemo` on provider values.

7. **Eliminate prop drilling without going global.** Options in order of preference:
   - **Composition / component inversion**: pass components as children instead of props, eliminating intermediary forwarding.
   - **Colocated context**: a context scoped to a subtree (not the entire app) avoids global pollution.
   - **Slots pattern**: pass content as JSX slots directly from the grandparent, skipping intermediate components.

8. **Measure before optimizing re-renders.** Open React DevTools Profiler, record an interaction, and check the "Ranked" view. Only optimize components with a significant render time. Apply `React.memo`, `useMemo`, and `useCallback` based on measurement — premature memoization adds cognitive cost for no gain.

9. **RSC reduces client state needs.** In Next.js App Router, data fetched in Server Components does not need client state at all — it is passed as props from the server. Migrate data-fetching `useEffect` hooks to Server Components wherever possible.

## References
- TanStack Query (React Query) documentation
- Zustand documentation (pmndrs/zustand)
- Redux Toolkit documentation (redux-toolkit.js.org)
- Dan Abramov — "Thinking in React" (react.dev)
- Kent C. Dodds — Application State Management with React
