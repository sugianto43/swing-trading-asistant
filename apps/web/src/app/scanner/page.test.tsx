import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchScanCandidates = vi.fn();
vi.mock("@/lib/queries/scanner", async () => {
  const actual = await vi.importActual<typeof import("@/lib/queries/scanner")>(
    "@/lib/queries/scanner",
  );
  return { ...actual, fetchScanCandidates: (filters: unknown) => fetchScanCandidates(filters) };
});

import ScannerPage from "./page";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ScannerPage />
    </QueryClientProvider>,
  );
}

describe("ScannerPage", () => {
  it("shows an error state when the request fails", async () => {
    fetchScanCandidates.mockRejectedValueOnce(new Error("boom"));
    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Couldn't load scan candidates/)).toBeInTheDocument(),
    );
  });

  it("renders the candidates table once results resolve", async () => {
    fetchScanCandidates.mockResolvedValueOnce({
      items: [
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
      ],
      total: 1,
    });
    renderPage();

    await waitFor(() => expect(screen.getByRole("link", { name: "BBCA" })).toBeInTheDocument());
  });

  it("shows an explicit empty state when no candidates match, not a blank screen", async () => {
    fetchScanCandidates.mockResolvedValueOnce({ items: [], total: 0 });
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("No candidates match these filters.")).toBeInTheDocument(),
    );
  });
});
