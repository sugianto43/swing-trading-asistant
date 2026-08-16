import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

let searchParams = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useSearchParams: () => searchParams,
}));

const fetchSnapshots = vi.fn();
const fetchInstrumentsById = vi.fn();
vi.mock("@/lib/queries/ai", () => ({
  fetchSnapshots: (filters: unknown) => fetchSnapshots(filters),
  analyzeQuestion: vi.fn(),
}));
vi.mock("@/lib/queries/instruments", () => ({
  fetchInstrumentsById: () => fetchInstrumentsById(),
}));

import { AiPageContent } from "./ai-page-content";

function renderContent() {
  fetchSnapshots.mockResolvedValue({ items: [], total: 0 });
  fetchInstrumentsById.mockResolvedValue(new Map());
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AiPageContent />
    </QueryClientProvider>,
  );
}

describe("AiPageContent", () => {
  it("prefills the form's symbol from URL search params", () => {
    searchParams = new URLSearchParams("symbol=BBCA");
    renderContent();

    expect(screen.getByLabelText("Symbol (optional)")).toHaveValue("BBCA");
  });

  it("shows the empty state when there are no past analyses", async () => {
    searchParams = new URLSearchParams();
    renderContent();

    await waitFor(() => expect(screen.getByText("No analyses yet.")).toBeInTheDocument());
  });

  it("shows a distinct error when snapshots fail to load", async () => {
    searchParams = new URLSearchParams();
    fetchInstrumentsById.mockResolvedValue(new Map());
    fetchSnapshots.mockRejectedValueOnce(new Error("network down"));
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <AiPageContent />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByText("Couldn't load past analyses. Check that the API is reachable and retry."),
      ).toBeInTheDocument(),
    );
  });
});
