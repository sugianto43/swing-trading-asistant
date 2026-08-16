import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/positions/equity-curve-chart", () => ({
  EquityCurveChart: ({ points }: { points: [string, number][] }) => (
    <div>equity points={points.length}</div>
  ),
}));

import { PerformanceSummary } from "./performance-summary";

describe("PerformanceSummary", () => {
  it("renders the summary stats and forwards the equity curve", () => {
    render(
      <PerformanceSummary
        summary={{
          initial_capital: 100_000_000,
          total_realized_pnl: 5_000_000,
          unrealized_pnl: 1_000_000,
          exposure: 20_000_000,
          closed_position_count: 4,
          win_rate_pct: 75,
          avg_win: 2_000_000,
          avg_loss: -500_000,
          expectancy: 1_100_000,
          profit_factor: 3.2,
          max_drawdown_pct: 12.5,
          sharpe_ratio: 1.8,
          equity_curve: [
            ["2024-01-01", 100_000_000],
            ["2024-02-01", 105_000_000],
          ],
        }}
      />,
    );

    expect(screen.getByText("Performance Summary")).toBeInTheDocument();
    expect(screen.getByText("5000000")).toBeInTheDocument();
    expect(screen.getByText("75.0%")).toBeInTheDocument();
    expect(screen.getByText("equity points=2")).toBeInTheDocument();
  });

  it("renders null metrics as a placeholder, not a crash", () => {
    render(
      <PerformanceSummary
        summary={{
          initial_capital: 0,
          total_realized_pnl: 0,
          unrealized_pnl: 0,
          exposure: 0,
          closed_position_count: 0,
          win_rate_pct: 0,
          avg_win: null,
          avg_loss: null,
          expectancy: null,
          profit_factor: null,
          max_drawdown_pct: 0,
          sharpe_ratio: null,
          equity_curve: [],
        }}
      />,
    );

    expect(screen.getAllByText("—")).toHaveLength(5);
  });
});
