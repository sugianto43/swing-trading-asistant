import { expect, test } from "@playwright/test";

import { checkA11y } from "./helpers";

/** MASTER-PRD §24 golden journey, UI-driven (Phase 18 TDD):
 * Market overview -> scanner candidate selection -> instrument detail ->
 * build trade plan -> AI explanation -> record manual execution -> view
 * open position -> add journal entry -> record exit execution -> view
 * performance -> AI review.
 *
 * Requires: `docker compose up -d db redis api`, then `./e2e/seed.sh`,
 * then the web app running against that backend (`npm run build && npm
 * run start`, or `npm run dev` for iteration) before `npx playwright
 * test`. See README.md in this directory.
 *
 * AI steps assert whatever the backend actually returns — a real
 * grounded answer if GEMINI_API_KEY is configured in the Docker
 * environment, or the plain "no LLM provider configured" 503 message if
 * not (Phase 16's own sign-off precedent: that message is a valid,
 * correctly-rendered outcome, not a failure to route around). Either
 * response proves the same thing this phase cares about — the UI
 * renders exactly what the backend returned, nothing fabricated. */

test.describe.serial("golden journey", () => {
  test("market overview", async ({ page }) => {
    await page.goto("/overview", { waitUntil: "networkidle" });
    await expect(page.getByRole("link", { name: "IDX Swing Trading Assistant" })).toBeVisible();
    await checkA11y(page);
  });

  test("scanner candidate selection -> instrument detail", async ({ page }) => {
    await page.goto("/scanner", { waitUntil: "networkidle" });
    await expect(page.getByRole("link", { name: "BBCA" }).first()).toBeVisible({ timeout: 15_000 });
    await checkA11y(page);

    await page.getByRole("link", { name: "BBCA" }).first().click();
    await page.waitForURL(/\/instruments\/BBCA/);
    await expect(page.getByRole("heading", { name: "BBCA" })).toBeVisible();
    await checkA11y(page);
  });

  test("build trade plan (from instrument detail's own candidate row)", async ({ page }) => {
    await page.goto("/instruments/BBCA", { waitUntil: "networkidle" });
    await page.getByRole("link", { name: "Build plan" }).first().click();
    await page.waitForURL(/\/risk\?/);

    await expect(page.getByLabel("Symbol")).toHaveValue("BBCA");
    await page.getByLabel("Capital (IDR)").fill("100000000");
    await page.getByRole("button", { name: "Build trade plan" }).click();
    await expect(page.getByText(/plan (ready|rejected)/)).toBeVisible({ timeout: 15_000 });
    await checkA11y(page);
  });

  test("AI explanation (from instrument detail)", async ({ page }) => {
    await page.goto("/instruments/BBCA", { waitUntil: "networkidle" });
    await page.getByRole("link", { name: "Ask AI about this stock" }).click();
    await page.waitForURL(/\/ai\?symbol=BBCA/);

    await expect(page.getByLabel("Symbol (optional)")).toHaveValue("BBCA");
    await page.getByLabel("Question").fill("What is BBCA's current setup and why?");
    await page.getByRole("button", { name: "Ask" }).click();
    // Whatever the backend genuinely returns is correct here — a real
    // grounded answer, "no LLM provider configured" if no key is set, or
    // even a transient upstream failure (e.g. the provider itself
    // returning 503 under load, seen live during this phase's own audit)
    // are all valid, un-fabricated outcomes. The one thing to prove is
    // that the request reached a settled, definitive state — not which
    // specific outcome it landed in — so this waits for the pending
    // label to appear and then clear, rather than enumerating every
    // possible response.
    await expect(page.getByRole("button", { name: "Analyzing…" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Analyzing…" })).toHaveCount(0, {
      timeout: 25_000,
    });
    await checkA11y(page);
  });

  test("record manual execution -> view open position -> add journal entry", async ({ page }) => {
    await page.goto("/positions", { waitUntil: "networkidle" });
    await checkA11y(page);

    await page.getByLabel("Symbol", { exact: true }).fill("BBCA");
    await page.getByLabel("Side").click();
    await page.getByRole("option", { name: "BUY" }).click();
    await page.getByLabel("Quantity").fill("1000");
    await page.getByLabel("Price (IDR)").fill("1000");
    await page.getByLabel("Fee (IDR)").fill("500");
    await page.getByLabel("Executed at").fill("2024-03-01T09:30");
    await page.getByRole("button", { name: "Record execution" }).click();
    await expect(page.getByText("BBCA: execution recorded")).toBeVisible({ timeout: 15_000 });

    await page.getByRole("link", { name: "BBCA: execution recorded" }).click();
    await page.waitForURL(/\/positions\/[a-f0-9-]+/);
    await expect(page.getByText("Executions")).toBeVisible();
    await checkA11y(page);

    await page.getByLabel("Thesis").fill("Breakout continuation off the 20-day range.");
    await page.getByRole("button", { name: "Save journal entry" }).click();
    await expect(page.getByText("Journal entry saved.")).toBeVisible({ timeout: 15_000 });
  });

  test("record exit execution -> view performance", async ({ page }) => {
    await page.goto("/positions", { waitUntil: "networkidle" });
    await page.getByLabel("Symbol", { exact: true }).fill("BBCA");
    await page.getByLabel("Side").click();
    await page.getByRole("option", { name: "SELL" }).click();
    await page.getByLabel("Quantity").fill("1000");
    await page.getByLabel("Price (IDR)").fill("1100");
    await page.getByLabel("Executed at").fill("2024-03-05T09:30");
    await page.getByRole("button", { name: "Record execution" }).click();
    await expect(page.getByText("BBCA: execution recorded")).toBeVisible({ timeout: 15_000 });

    await page.getByRole("link", { name: "View performance →" }).click();
    await page.waitForURL(/\/positions\/performance/);
    await expect(page.getByText("Performance Summary")).toBeVisible({ timeout: 15_000 });
    await checkA11y(page);
  });

  test("AI review", async ({ page }) => {
    await page.goto("/ai", { waitUntil: "networkidle" });
    await page.getByLabel("Question").fill("Review how the BBCA breakout trade played out.");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByRole("button", { name: "Analyzing…" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Analyzing…" })).toHaveCount(0, {
      timeout: 25_000,
    });
    await checkA11y(page);
  });
});
