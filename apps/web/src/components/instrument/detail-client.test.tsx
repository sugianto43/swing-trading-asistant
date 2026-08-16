import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchInstrument = vi.fn();
const fetchRecentPriceBars = vi.fn();
const fetchRecentIndicators = vi.fn();
const fetchInstrumentCandidates = vi.fn();

vi.mock("@/lib/queries/instruments", () => ({
  fetchInstrument: (symbol: string) => fetchInstrument(symbol),
  fetchRecentPriceBars: (symbol: string) => fetchRecentPriceBars(symbol),
}));
vi.mock("@/lib/queries/indicators", () => ({
  fetchRecentIndicators: (symbol: string) => fetchRecentIndicators(symbol),
}));
vi.mock("@/lib/queries/scanner", () => ({
  fetchInstrumentCandidates: (symbol: string) => fetchInstrumentCandidates(symbol),
}));
// The real chart mounts a canvas via lightweight-charts, irrelevant to
// this component's own loading/error/empty-state branching.
vi.mock("@/components/instrument/price-chart", () => ({
  PriceChart: () => <div data-testid="price-chart" />,
}));

import { InstrumentDetailClient } from "./detail-client";

function renderClient(symbol: string) {
  fetchRecentPriceBars.mockResolvedValue([]);
  fetchRecentIndicators.mockResolvedValue([]);
  fetchInstrumentCandidates.mockResolvedValue([]);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <InstrumentDetailClient symbol={symbol} />
    </QueryClientProvider>,
  );
}

const INSTRUMENT = {
  id: "1",
  symbol: "BBCA",
  company_name: "Bank Central Asia Tbk",
  exchange: "IDX",
  currency: "IDR",
  security_type: "EQUITY",
  sector: "Banking",
  subsector: null,
  listing_date: null,
  delisting_date: null,
  status: "ACTIVE",
  source: "fixture",
  source_symbol: "BBCA.JK",
};

describe("InstrumentDetailClient", () => {
  it("shows a not-found state for an unseeded symbol, distinct from a generic error", async () => {
    fetchInstrument.mockRejectedValueOnce(new Error("NOT_FOUND"));
    renderClient("NOPE");

    await waitFor(() =>
      expect(screen.getByText('No instrument found for "NOPE".')).toBeInTheDocument(),
    );
  });

  it("shows a generic error state for a non-404 failure", async () => {
    fetchInstrument.mockRejectedValueOnce(new Error("network down"));
    renderClient("BBCA");

    await waitFor(() =>
      expect(screen.getByText("Couldn't load this instrument.")).toBeInTheDocument(),
    );
  });

  it("renders the instrument header and chart once data resolves", async () => {
    fetchInstrument.mockResolvedValueOnce(INSTRUMENT);
    renderClient("BBCA");

    await waitFor(() => expect(screen.getByText("BBCA")).toBeInTheDocument());
    expect(await screen.findByTestId("price-chart")).toBeInTheDocument();
  });

  it("shows a distinct error when price/indicator data fails to load, not an empty chart", async () => {
    fetchInstrument.mockResolvedValueOnce(INSTRUMENT);
    renderClient("BBCA");
    fetchRecentPriceBars.mockRejectedValueOnce(new Error("network down"));

    await waitFor(() => expect(screen.getByText("BBCA")).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getByText("Couldn't load price history.")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("price-chart")).not.toBeInTheDocument();
  });

  it("shows a distinct error when recent setups fail to load, not an empty list", async () => {
    fetchInstrument.mockResolvedValueOnce(INSTRUMENT);
    renderClient("BBCA");
    fetchInstrumentCandidates.mockRejectedValueOnce(new Error("network down"));

    await waitFor(() => expect(screen.getByText("BBCA")).toBeInTheDocument());
    await waitFor(() =>
      expect(screen.getByText("Couldn't load recent setups.")).toBeInTheDocument(),
    );
    expect(
      screen.queryByText("No scan candidates for this instrument yet."),
    ).not.toBeInTheDocument();
  });
});
