import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchTradePlan = vi.fn();
const fetchInstrumentsById = vi.fn();
vi.mock("@/lib/queries/risk", () => ({
  fetchTradePlan: (id: string) => fetchTradePlan(id),
}));
vi.mock("@/lib/queries/instruments", () => ({
  fetchInstrumentsById: () => fetchInstrumentsById(),
}));

import { TradePlanDetailClient } from "./trade-plan-detail-client";

function renderClient(id: string) {
  fetchInstrumentsById.mockResolvedValue(new Map());
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <TradePlanDetailClient id={id} />
    </QueryClientProvider>,
  );
}

const VALID_PLAN = {
  id: "1",
  instrument_id: "uuid-1",
  scan_candidate_id: "candidate-1",
  setup_type: "BREAKOUT",
  plan_date: "2024-03-01",
  risk_version: "v1",
  score_version: "v1",
  indicator_version: "v1",
  status: "VALID",
  rejection_reasons: [],
  entry_price: 1050,
  stop_price: 1000,
  target_prices: [],
  quantity: 100,
  allocation_amount: 105_000,
  allocation_pct: 10.5,
  max_loss_amount: 5_000,
  risk_reward_ratio: 2.0,
  assumptions: {},
  invalidation_conditions: ["close falls back below 1000"],
  created_at: "2024-03-01T00:00:00Z",
  updated_at: "2024-03-01T00:00:00Z",
};

describe("TradePlanDetailClient", () => {
  it("shows a not-found state for an unknown id, distinct from a generic error", async () => {
    fetchTradePlan.mockRejectedValueOnce(new Error("NOT_FOUND"));
    renderClient("nope");

    await waitFor(() =>
      expect(screen.getByText('No trade plan found for "nope".')).toBeInTheDocument(),
    );
  });

  it("shows a generic error state for a non-404 failure", async () => {
    fetchTradePlan.mockRejectedValueOnce(new Error("network down"));
    renderClient("1");

    await waitFor(() =>
      expect(screen.getByText("Couldn't load this trade plan.")).toBeInTheDocument(),
    );
  });

  it("renders the plan result and invalidation conditions once resolved", async () => {
    fetchTradePlan.mockResolvedValueOnce(VALID_PLAN);
    renderClient("1");

    await waitFor(() => expect(screen.getByText("VALID")).toBeInTheDocument());
    expect(screen.getByText("close falls back below 1000")).toBeInTheDocument();
  });

  it("falls back to the raw instrument_id when the instrument lookup has no match", async () => {
    fetchTradePlan.mockResolvedValueOnce(VALID_PLAN);
    renderClient("1");

    await waitFor(() => expect(screen.getByText("uuid-1: plan ready")).toBeInTheDocument());
  });

  it("falls back to the raw instrument_id when the instrument lookup itself fails", async () => {
    fetchTradePlan.mockResolvedValueOnce(VALID_PLAN);
    fetchInstrumentsById.mockReset();
    fetchInstrumentsById.mockRejectedValueOnce(new Error("instruments request failed"));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <TradePlanDetailClient id="1" />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText("uuid-1: plan ready")).toBeInTheDocument());
  });

  it("renders assumptions as JSON when present, omitted when empty", async () => {
    fetchTradePlan.mockResolvedValueOnce({
      ...VALID_PLAN,
      assumptions: { slippage_bps: 5 },
    });
    renderClient("1");

    await waitFor(() => expect(screen.getByText("Assumptions:")).toBeInTheDocument());
    expect(screen.getByText(/"slippage_bps": 5/)).toBeInTheDocument();
  });

  it("omits the assumptions block when assumptions is empty", async () => {
    fetchTradePlan.mockResolvedValueOnce(VALID_PLAN);
    renderClient("1");

    await waitFor(() => expect(screen.getByText("VALID")).toBeInTheDocument());
    expect(screen.queryByText("Assumptions:")).not.toBeInTheDocument();
  });
});
