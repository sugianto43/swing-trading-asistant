import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchPerformanceSummary = vi.fn();
const fetchPerformanceBySetup = vi.fn();
const fetchPerformanceBySector = vi.fn();
const fetchPerformanceByHoldingPeriod = vi.fn();
const fetchPerformanceByScoreBucket = vi.fn();
const fetchPerformanceBehavior = vi.fn();
vi.mock("@/lib/queries/performance", () => ({
  fetchPerformanceSummary: () => fetchPerformanceSummary(),
  fetchPerformanceBySetup: () => fetchPerformanceBySetup(),
  fetchPerformanceBySector: () => fetchPerformanceBySector(),
  fetchPerformanceByHoldingPeriod: () => fetchPerformanceByHoldingPeriod(),
  fetchPerformanceByScoreBucket: () => fetchPerformanceByScoreBucket(),
  fetchPerformanceBehavior: () => fetchPerformanceBehavior(),
}));
vi.mock("@/components/positions/equity-curve-chart", () => ({
  EquityCurveChart: () => <div>equity curve</div>,
}));

import { PerformancePageContent } from "./performance-page-content";

const EMPTY_SUMMARY = {
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
};

function mockAllSuccess() {
  fetchPerformanceSummary.mockResolvedValue(EMPTY_SUMMARY);
  fetchPerformanceBySetup.mockResolvedValue([]);
  fetchPerformanceBySector.mockResolvedValue([]);
  fetchPerformanceByHoldingPeriod.mockResolvedValue([]);
  fetchPerformanceByScoreBucket.mockResolvedValue([]);
  fetchPerformanceBehavior.mockResolvedValue([]);
}

function renderContent() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PerformancePageContent />
    </QueryClientProvider>,
  );
}

describe("PerformancePageContent", () => {
  it("renders the summary and all four group breakdowns once loaded", async () => {
    mockAllSuccess();
    renderContent();

    await waitFor(() => expect(screen.getByText("Performance Summary")).toBeInTheDocument());
    expect(screen.getByText("By Setup")).toBeInTheDocument();
    expect(screen.getByText("By Sector")).toBeInTheDocument();
    expect(screen.getByText("By Holding Period")).toBeInTheDocument();
    expect(screen.getByText("By Score Bucket")).toBeInTheDocument();
    expect(screen.getByText("Behavior")).toBeInTheDocument();
  });

  it("shows a distinct error state when any query fails, not a partial dashboard", async () => {
    mockAllSuccess();
    fetchPerformanceBehavior.mockRejectedValueOnce(new Error("network down"));
    renderContent();

    await waitFor(() =>
      expect(screen.getByText("Couldn't load performance data.")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Performance Summary")).not.toBeInTheDocument();
  });
});
