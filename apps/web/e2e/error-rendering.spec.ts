import { expect, test } from "@playwright/test";

/** "No client-side fabrication of any value the backend didn't return"
 * (Phase 18 TDD audit item) — the adversarial complement to
 * golden-journey.spec.ts's happy path. Live-verifies against the real
 * backend that a genuine request failure renders the backend's own
 * message verbatim, not a generic fallback — the exact class of bug
 * found and fixed in positions.ts during this phase's own implementation
 * (app/errors.py's global exception handler wraps every error in
 * {"error": {"message"}}, not FastAPI's bare {"detail"}; a prior version
 * of errorDetail() read the wrong field and silently fell back to a
 * generic string for every single error). Only a mocked unit test
 * covered this before — mocking the wrong envelope shape would pass
 * regardless of whether the real parsing logic is correct, which is
 * exactly what happened the first time. This spec can't be fooled that
 * way since nothing about the response is mocked. */
test.describe("error rendering — no client-side fabrication", () => {
  test("overselling renders the backend's real message, not a generic fallback", async ({
    page,
  }) => {
    await page.goto("/positions", { waitUntil: "networkidle" });

    // Sell a wildly larger quantity than any position seeded this phase
    // could possibly have open — guaranteed to be a real oversell
    // against whatever the backend's actual state is, no matter what
    // earlier specs happened to leave behind.
    await page.getByLabel("Symbol", { exact: true }).fill("BBCA");
    await page.getByLabel("Side").click();
    await page.getByRole("option", { name: "SELL" }).click();
    await page.getByLabel("Quantity").fill("999999999");
    await page.getByLabel("Price (IDR)").fill("1000");
    await page.getByLabel("Executed at").fill("2024-03-06T09:30");
    await page.getByRole("button", { name: "Record execution" }).click();

    const errorText = page.locator("p.text-destructive");
    await expect(errorText).toBeVisible({ timeout: 15_000 });
    const message = await errorText.textContent();

    // The generic fallback string is the one thing this must never be —
    // that's precisely what the bug produced for every error, always.
    expect(message).not.toContain("execution request failed");
    // The real backend message (app/positions/position_engine.py) is one
    // of two forms depending on whether BBCA has any open quantity left
    // from earlier specs in this run: "cannot sell N shares — only M
    // open" or "cannot sell without an open position". Both mention
    // "sell", neither is the generic fallback — that's the actual thing
    // being proven here, not the exact wording of either variant.
    expect(message).toMatch(/cannot sell/i);
  });
});
