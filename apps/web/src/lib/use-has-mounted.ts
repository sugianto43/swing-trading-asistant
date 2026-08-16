import { useSyncExternalStore } from "react";

function subscribe(): () => void {
  return () => {};
}

/**
 * True only after the client has hydrated. Needed for anything that
 * reads browser-only state on first render (theme from localStorage,
 * matchMedia, etc.) — such values resolve synchronously on the client's
 * very first render, before hydration reconciles, so naively branching
 * on "is the value still unresolved?" doesn't work: it's never
 * unresolved on the client, only during SSR, which causes exactly the
 * server/client markup mismatch this hook exists to avoid.
 *
 * Uses useSyncExternalStore (getServerSnapshot=false, getSnapshot=true)
 * rather than a `useEffect(() => setState(true), [])` pattern: both
 * render `false` on the server AND on the client's first (hydrating)
 * pass, then React schedules the flip to `true` — but this avoids the
 * synchronous setState-in-effect this repo's lint config flags.
 */
export function useHasMounted(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
