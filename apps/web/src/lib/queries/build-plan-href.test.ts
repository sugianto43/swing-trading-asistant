import { describe, expect, it } from "vitest";

import { buildPlanHref } from "./build-plan-href";
import type { ScanCandidate } from "./scanner";

describe("buildPlanHref", () => {
  it("builds a /risk link carrying symbol, setup, and date", () => {
    const candidate = {
      symbol: "BBCA",
      setup_type: "BREAKOUT",
      scan_date: "2024-03-01",
    } as ScanCandidate;

    expect(buildPlanHref(candidate)).toBe("/risk?symbol=BBCA&setup=BREAKOUT&date=2024-03-01");
  });
});
