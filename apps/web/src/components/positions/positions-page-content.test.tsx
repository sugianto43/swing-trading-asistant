import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

let searchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
}));

const fetchPositions = vi.fn();
const fetchInstrumentsById = vi.fn();
vi.mock("@/lib/queries/positions", () => ({
  fetchPositions: (filters: unknown) => fetchPositions(filters),
  recordExecution: vi.fn(),
}));
vi.mock("@/lib/queries/instruments", () => ({
  fetchInstrumentsById: () => fetchInstrumentsById(),
}));

import { PositionsPageContent } from "./positions-page-content";

function renderContent() {
  fetchPositions.mockResolvedValue({ items: [], total: 0 });
  fetchInstrumentsById.mockResolvedValue(new Map());
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PositionsPageContent />
    </QueryClientProvider>,
  );
}

describe("PositionsPageContent", () => {
  it("prefills the execution form from URL search params", () => {
    searchParams = new URLSearchParams("symbol=BBCA&trade_plan_id=plan-1");
    renderContent();

    expect(screen.getByLabelText("Symbol")).toHaveValue("BBCA");
  });

  it("shows the empty state when there are no positions", async () => {
    searchParams = new URLSearchParams();
    renderContent();

    await waitFor(() => expect(screen.getByText("No positions yet.")).toBeInTheDocument());
  });

  it("shows a distinct error when positions fail to load", async () => {
    searchParams = new URLSearchParams();
    fetchInstrumentsById.mockResolvedValue(new Map());
    fetchPositions.mockRejectedValueOnce(new Error("network down"));
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <PositionsPageContent />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByText("Couldn't load positions. Check that the API is reachable and retry."),
      ).toBeInTheDocument(),
    );
  });

  it("links to the performance dashboard", () => {
    searchParams = new URLSearchParams();
    renderContent();

    expect(screen.getByRole("link", { name: "View performance →" })).toHaveAttribute(
      "href",
      "/positions/performance",
    );
  });

  it("refetches with the filter bar's symbol once it changes", async () => {
    const user = userEvent.setup();
    searchParams = new URLSearchParams();
    renderContent();

    await waitFor(() => expect(fetchPositions).toHaveBeenCalledWith({}));

    await user.type(screen.getByLabelText("Symbol filter"), "BBCA");

    await waitFor(() =>
      expect(fetchPositions).toHaveBeenCalledWith(expect.objectContaining({ symbol: "BBCA" })),
    );
  });
});
