import { defineConfig, devices } from "@playwright/test";

/** Golden-journey/a11y E2E (Phase 18). Runs against a real Docker
 * backend (db/redis/api) + real seeded data — see apps/web/e2e/README.md
 * for the prerequisite steps. Not run in CI (no Docker there); this is a
 * local/manual gate, same discipline every phase's sign-off has used all
 * session, now formalized into a committed, reproducible spec instead of
 * a scratchpad script. */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  // fullyParallel:false only serializes tests within one file — different
  // spec files still run concurrently across workers by default. Every
  // spec here mutates the same shared, persistent Docker database with
  // no per-test isolation/reset, so the whole run is forced onto one
  // worker: today's assertions happen to be order-independent, but
  // nothing should rely on that holding for specs added later.
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
