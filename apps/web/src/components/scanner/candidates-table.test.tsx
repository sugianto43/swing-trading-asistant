import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CandidatesTable } from "./candidates-table";
import type { ScanCandidate } from "@/lib/queries/scanner";

function makeCandidate(overrides: Partial<ScanCandidate> = {}): ScanCandidate {
  return {
    symbol: "BBCA",
    scan_date: "2024-03-01",
    setup_type: "BREAKOUT",
    indicator_version: "v1",
    score_version: "v1",
    composite_score: 82.4,
    trend_score: 10,
    momentum_score: 20,
    volume_score: 30,
    price_structure_score: 10,
    volatility_score: 5,
    setup_quality_score: 5,
    risk_reward_score: 2.5,
    qualifying_conditions: [],
    invalidation_conditions: [],
    ...overrides,
  };
}

describe("CandidatesTable", () => {
  it("renders an explicit empty state rather than a blank table", () => {
    render(<CandidatesTable candidates={[]} />);
    expect(screen.getByText("No candidates match these filters.")).toBeInTheDocument();
  });

  it("renders a row per candidate, linking the symbol to its detail page", () => {
    render(<CandidatesTable candidates={[makeCandidate()]} />);

    const link = screen.getByRole("link", { name: "BBCA" });
    expect(link).toHaveAttribute("href", "/instruments/BBCA");
    expect(screen.getByText("BREAKOUT")).toBeInTheDocument();
    expect(screen.getByText("82.4")).toBeInTheDocument();
  });
});
