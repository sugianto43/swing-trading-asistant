import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BreadthStats } from "./breadth-stats";
import type { BreadthSnapshot } from "@/lib/queries/breadth";

function makeBreadth(overrides: Partial<BreadthSnapshot> = {}): BreadthSnapshot {
  return {
    id: "1",
    as_of: "2024-03-01",
    breadth_version: "v1",
    universe_size: 50,
    pct_above_sma50: 62.5,
    pct_above_sma200: 40,
    advancers: 30,
    decliners: 20,
    unchanged: 0,
    new_highs_20: 5,
    new_lows_20: 2,
    regime: "RISK_ON",
    regime_version: "v1",
    created_at: "2024-03-01T00:00:00Z",
    ...overrides,
  };
}

describe("BreadthStats", () => {
  it("renders the core stats and the as-of date", () => {
    render(<BreadthStats breadth={makeBreadth()} />);

    expect(screen.getByText("50")).toBeInTheDocument();
    expect(screen.getByText("62.5%")).toBeInTheDocument();
    expect(screen.getByText("As of 2024-03-01")).toBeInTheDocument();
  });

  it("renders an em dash for a null percentage rather than fabricating a value", () => {
    render(<BreadthStats breadth={makeBreadth({ pct_above_sma200: null })} />);

    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it.each([
    ["RISK_ON", "Risk On"],
    ["RISK_OFF", "Risk Off"],
    ["NEUTRAL", "Neutral"],
  ] as const)("renders the %s regime as %s", (regime, label) => {
    render(<BreadthStats breadth={makeBreadth({ regime })} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });
});
