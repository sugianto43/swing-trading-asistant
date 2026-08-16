import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PerformanceGroupTable } from "./performance-group-table";

describe("PerformanceGroupTable", () => {
  it("shows an empty state distinct from a table", () => {
    render(<PerformanceGroupTable title="By Setup" groups={[]} keyLabel="Setup" />);

    expect(screen.getByText("No closed positions yet.")).toBeInTheDocument();
  });

  it("renders each group's stats", () => {
    render(
      <PerformanceGroupTable
        title="By Setup"
        keyLabel="Setup"
        groups={[
          { key: "BREAKOUT", closed_position_count: 3, total_realized_pnl: 15000, win_rate_pct: 66.7 },
        ]}
      />,
    );

    expect(screen.getByText("BREAKOUT")).toBeInTheDocument();
    expect(screen.getByText("15000")).toBeInTheDocument();
    expect(screen.getByText("66.7%")).toBeInTheDocument();
  });

  it("renders a null key as a placeholder, not a crash", () => {
    render(
      <PerformanceGroupTable
        title="By Sector"
        keyLabel="Sector"
        groups={[{ key: null, closed_position_count: 1, total_realized_pnl: 0, win_rate_pct: 0 }]}
      />,
    );

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
