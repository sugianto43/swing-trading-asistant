import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchSnapshot = vi.fn();
vi.mock("@/lib/queries/ai", () => ({
  fetchSnapshot: (id: string) => fetchSnapshot(id),
}));

import { SnapshotDetailClient } from "./snapshot-detail-client";

function renderClient(id: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <SnapshotDetailClient id={id} />
    </QueryClientProvider>,
  );
}

const SNAPSHOT = {
  id: "1",
  instrument_id: "uuid-1",
  provider: "gemini",
  model: "gemini-2.0-flash",
  prompt_version: "v1",
  question: "What is BBCA's setup?",
  tool_calls: [],
  structured_data_snapshot: [],
  response: "BBCA shows a breakout setup.",
  guardrail_flags: [],
  created_at: "2024-03-01T00:00:00Z",
};

describe("SnapshotDetailClient", () => {
  it("shows a not-found state for an unknown id, distinct from a generic error", async () => {
    fetchSnapshot.mockRejectedValueOnce(new Error("NOT_FOUND"));
    renderClient("nope");

    await waitFor(() => expect(screen.getByText('No analysis found for "nope".')).toBeInTheDocument());
  });

  it("shows a generic error state for a non-404 failure", async () => {
    fetchSnapshot.mockRejectedValueOnce(new Error("network down"));
    renderClient("1");

    await waitFor(() => expect(screen.getByText("Couldn't load this analysis.")).toBeInTheDocument());
  });

  it("renders the analysis once resolved", async () => {
    fetchSnapshot.mockResolvedValueOnce(SNAPSHOT);
    renderClient("1");

    await waitFor(() => expect(screen.getByText("BBCA shows a breakout setup.")).toBeInTheDocument());
  });
});
