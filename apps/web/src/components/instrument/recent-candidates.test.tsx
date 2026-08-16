import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RecentCandidates } from "./recent-candidates";

describe("RecentCandidates", () => {
  it("renders an explicit empty state rather than a blank card", () => {
    render(<RecentCandidates candidates={[]} />);
    expect(screen.getByText("No scan candidates for this instrument yet.")).toBeInTheDocument();
  });

  it("renders one entry per candidate", () => {
    render(
      <RecentCandidates
        candidates={[
          {
            symbol: "BBCA",
            scan_date: "2024-03-01",
            setup_type: "BREAKOUT",
            indicator_version: "v1",
            score_version: "v1",
            composite_score: 82.4,
            trend_score: 0,
            momentum_score: 0,
            volume_score: 0,
            price_structure_score: 0,
            volatility_score: 0,
            setup_quality_score: 0,
            risk_reward_score: 0,
            qualifying_conditions: [],
            invalidation_conditions: [],
          },
        ]}
      />,
    );

    expect(screen.getByText("BREAKOUT")).toBeInTheDocument();
    expect(screen.getByText("82.4")).toBeInTheDocument();
  });
});
