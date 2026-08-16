import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Without vitest's `test.globals: true` (deliberately not set, to keep
// test-only globals out of app code's type-checking), @testing-library/
// react's auto-cleanup can't find a global afterEach to hook into, so it
// silently never runs — DOM from one test leaks into the next test in
// the same file. Registering it explicitly here fixes that project-wide.
afterEach(() => {
  cleanup();
});

// Module-level vi.fn() mocks (the standard pattern for vi.mock("@/lib/...")
// in this codebase) otherwise accumulate call history across every test in
// the file — a later test's `mock.calls[0]` silently picks up an earlier
// test's call instead of its own. Clearing between tests project-wide
// avoids re-discovering this once per test file.
afterEach(() => {
  vi.clearAllMocks();
});

// jsdom doesn't implement the Pointer Events capture methods Radix's
// Select uses internally — clicking an option throws
// "target.hasPointerCapture is not a function" the first time a test
// exercises Select via userEvent. No-op stubs are enough; tests only
// need the calls not to throw, not real capture semantics.
if (typeof window !== "undefined") {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
  }
  if (!Element.prototype.setPointerCapture) {
    Element.prototype.setPointerCapture = () => {};
  }
  if (!Element.prototype.releasePointerCapture) {
    Element.prototype.releasePointerCapture = () => {};
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => {};
  }
}

// jsdom doesn't implement matchMedia — next-themes' system-theme
// detection calls it on mount, so anything using ThemeProvider needs
// this polyfilled for tests to run at all.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as unknown as MediaQueryList;
}
