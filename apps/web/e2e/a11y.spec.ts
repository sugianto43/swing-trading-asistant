import { expect, test } from "@playwright/test";

import { checkA11y } from "./helpers";

/** Accessibility checks for the routes the golden journey doesn't
 * naturally visit. The journey itself already checks /overview,
 * /scanner, /instruments/[symbol], /risk, /ai, /positions,
 * /positions/[id], /positions/performance — this file covers the rest,
 * completing Phase 18 TDD's "every screen built in Phases 12-17"
 * requirement across all 13 real routes. */
test.describe("accessibility — remaining routes", () => {
  test("home", async ({ page }) => {
    await page.goto("/", { waitUntil: "networkidle" });
    await checkA11y(page);
  });

  test("alerts", async ({ page }) => {
    await page.goto("/alerts", { waitUntil: "networkidle" });
    await checkA11y(page);
  });

  test("trade plan detail", async ({ page }) => {
    // Navigates through the real list rather than hardcoding a seeded
    // id — the id is an ephemeral artifact of whatever data happens to
    // exist, not something this spec should assume.
    await page.goto("/risk", { waitUntil: "networkidle" });
    const firstRow = page.locator("table tbody tr").first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.getByRole("link").first().click();
    await page.waitForURL(/\/risk\/[a-f0-9-]+/);
    await checkA11y(page);
  });

  test("AI snapshot detail", async ({ page }) => {
    await page.goto("/ai", { waitUntil: "networkidle" });
    const firstRow = page.locator("table tbody tr").first();
    await expect(firstRow).toBeVisible({ timeout: 15_000 });
    await firstRow.getByRole("link").first().click();
    await page.waitForURL(/\/ai\/[a-f0-9-]+/);
    await checkA11y(page);
  });
});
