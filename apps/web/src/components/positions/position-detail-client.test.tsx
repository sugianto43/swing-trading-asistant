import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchPosition = vi.fn();
const fetchExecutions = vi.fn();
const fetchJournal = vi.fn();
const fetchInstrumentsById = vi.fn();
vi.mock("@/lib/queries/positions", () => ({
  fetchPosition: (id: string) => fetchPosition(id),
  fetchExecutions: (id: string) => fetchExecutions(id),
  fetchJournal: (id: string) => fetchJournal(id),
  upsertJournal: vi.fn(),
}));
vi.mock("@/lib/queries/instruments", () => ({
  fetchInstrumentsById: () => fetchInstrumentsById(),
}));

import { PositionDetailClient } from "./position-detail-client";

function renderClient(id: string) {
  fetchInstrumentsById.mockResolvedValue(new Map());
  fetchExecutions.mockResolvedValue([]);
  fetchJournal.mockResolvedValue(null);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PositionDetailClient id={id} />
    </QueryClientProvider>,
  );
}

const POSITION = {
  id: "pos-1",
  instrument_id: "uuid-1",
  trade_plan_id: null,
  status: "OPEN",
  quantity_open: 100,
  avg_entry_price: 1050,
  avg_entry_fee_per_share: 5,
  cumulative_quantity_bought: 100,
  cumulative_entry_fees: 500,
  cumulative_exit_fees: 100,
  realized_pnl: 0,
  opened_at: "2024-03-01T02:30:00Z",
  closed_at: null,
  created_at: "2024-03-01T02:30:00Z",
  updated_at: "2024-03-01T02:30:00Z",
};

describe("PositionDetailClient", () => {
  it("shows a not-found state for an unknown id, distinct from a generic error", async () => {
    fetchPosition.mockRejectedValueOnce(new Error("NOT_FOUND"));
    renderClient("nope");

    await waitFor(() => expect(screen.getByText('No position found for "nope".')).toBeInTheDocument());
  });

  it("shows a generic error state for a non-404 failure", async () => {
    fetchPosition.mockRejectedValueOnce(new Error("network down"));
    renderClient("1");

    await waitFor(() => expect(screen.getByText("Couldn't load this position.")).toBeInTheDocument());
  });

  it("renders position fields once resolved", async () => {
    fetchPosition.mockResolvedValueOnce(POSITION);
    renderClient("pos-1");

    await waitFor(() => expect(screen.getByText("OPEN")).toBeInTheDocument());
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("shows an empty-executions message distinct from a load failure", async () => {
    fetchPosition.mockResolvedValueOnce(POSITION);
    renderClient("pos-1");

    await waitFor(() => expect(screen.getByText("No executions recorded yet.")).toBeInTheDocument());
  });

  it("renders execution history rows when present", async () => {
    fetchPosition.mockResolvedValueOnce(POSITION);
    fetchInstrumentsById.mockResolvedValue(new Map());
    fetchJournal.mockResolvedValue(null);
    fetchExecutions.mockResolvedValueOnce([
      {
        id: "exec-1",
        position_id: "pos-1",
        instrument_id: "uuid-1",
        trade_plan_id: null,
        side: "BUY",
        quantity: 100,
        price: 1050,
        fee: 500,
        realized_pnl_impact: null,
        executed_at: "2024-03-01T02:30:00Z",
        notes: null,
        created_at: "2024-03-01T02:30:00Z",
      },
    ]);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <PositionDetailClient id="pos-1" />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText("BUY")).toBeInTheDocument());
  });

  it("renders the journal form as an empty form when no journal exists yet, not an error", async () => {
    fetchPosition.mockResolvedValueOnce(POSITION);
    renderClient("pos-1");

    await waitFor(() => expect(screen.getByLabelText("Thesis")).toBeInTheDocument());
    expect(screen.queryByText("Couldn't load the journal entry.")).not.toBeInTheDocument();
  });

  it("falls back to the raw instrument_id when the instrument lookup fails", async () => {
    fetchPosition.mockResolvedValueOnce(POSITION);
    fetchInstrumentsById.mockReset();
    fetchInstrumentsById.mockRejectedValueOnce(new Error("instruments request failed"));
    fetchExecutions.mockResolvedValue([]);
    fetchJournal.mockResolvedValue(null);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <PositionDetailClient id="pos-1" />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText("uuid-1")).toBeInTheDocument());
  });
});
