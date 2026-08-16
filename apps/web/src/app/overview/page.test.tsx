import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchLatestBreadth = vi.fn();
const fetchSectorPerformance = vi.fn();
vi.mock("@/lib/queries/breadth", () => ({ fetchLatestBreadth: () => fetchLatestBreadth() }));
vi.mock("@/lib/queries/sector-performance", () => ({
  fetchSectorPerformance: (asOf: string) => fetchSectorPerformance(asOf),
}));

import OverviewPage from "./page";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <OverviewPage />
    </QueryClientProvider>,
  );
}

const BREADTH = {
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
};

describe("OverviewPage", () => {
  it("shows a loading state before breadth resolves", () => {
    fetchLatestBreadth.mockImplementation(() => new Promise(() => {}));
    renderPage();

    expect(screen.queryByText("As of 2024-03-01")).not.toBeInTheDocument();
  });

  it("shows an explicit empty state when no breadth has been computed yet", async () => {
    fetchLatestBreadth.mockRejectedValueOnce(new Error("NOT_FOUND"));
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("No market breadth computed yet.")).toBeInTheDocument(),
    );
  });

  it("shows a generic error state for a non-404 failure, distinct from the empty state", async () => {
    fetchLatestBreadth.mockRejectedValueOnce(new Error("network down"));
    renderPage();

    await waitFor(() => expect(screen.getByText("Couldn't load market breadth.")).toBeInTheDocument());
    expect(screen.queryByText("No market breadth computed yet.")).not.toBeInTheDocument();
  });

  it("chains sector-performance off the breadth's own as_of, not today's date", async () => {
    fetchLatestBreadth.mockResolvedValueOnce(BREADTH);
    fetchSectorPerformance.mockResolvedValueOnce([]);
    renderPage();

    await waitFor(() => expect(fetchSectorPerformance).toHaveBeenCalledWith("2024-03-01"));
  });

  it("renders breadth stats and sector performance once both resolve", async () => {
    fetchLatestBreadth.mockResolvedValueOnce(BREADTH);
    fetchSectorPerformance.mockResolvedValueOnce([
      { sector: "Banking", instrument_count: 5, avg_return_pct: 2.1 },
    ]);
    renderPage();

    await waitFor(() => expect(screen.getByText("As of 2024-03-01")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Banking")).toBeInTheDocument());
  });

  it("shows a distinct error for a sector-performance failure, not a fabricated empty result", async () => {
    fetchLatestBreadth.mockResolvedValueOnce(BREADTH);
    fetchSectorPerformance.mockRejectedValueOnce(new Error("network down"));
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("Couldn't load sector performance.")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText("No sector performance data for this date yet."),
    ).not.toBeInTheDocument();
  });
});
