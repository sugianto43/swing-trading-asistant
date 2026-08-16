import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

let searchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
}));

const fetchTradePlans = vi.fn();
const fetchInstrumentsById = vi.fn();
vi.mock("@/lib/queries/risk", () => ({
  fetchTradePlans: (filters: unknown) => fetchTradePlans(filters),
}));
vi.mock("@/lib/queries/instruments", () => ({
  fetchInstrumentsById: () => fetchInstrumentsById(),
}));

import { RiskPageContent } from "./risk-page-content";

function renderContent() {
  fetchTradePlans.mockResolvedValue({ items: [], total: 0 });
  fetchInstrumentsById.mockResolvedValue(new Map());
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <RiskPageContent />
    </QueryClientProvider>,
  );
}

describe("RiskPageContent", () => {
  it("prefills the form from URL search params", () => {
    searchParams = new URLSearchParams("symbol=BBCA&setup=BREAKOUT&date=2024-03-01");
    renderContent();

    expect(screen.getByLabelText("Symbol")).toHaveValue("BBCA");
    expect(screen.getByLabelText("Plan date")).toHaveValue("2024-03-01");
  });

  it("shows the empty state when there are no existing trade plans", async () => {
    searchParams = new URLSearchParams();
    renderContent();

    await waitFor(() => expect(screen.getByText("No trade plans yet.")).toBeInTheDocument());
  });

  it("shows a distinct error when trade plans fail to load", async () => {
    searchParams = new URLSearchParams();
    fetchInstrumentsById.mockResolvedValue(new Map());
    fetchTradePlans.mockRejectedValueOnce(new Error("network down"));
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <RiskPageContent />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByText("Couldn't load trade plans. Check that the API is reachable and retry."),
      ).toBeInTheDocument(),
    );
  });
});
