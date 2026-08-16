import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const fetchAlerts = vi.fn();
const fetchInstrumentsById = vi.fn();
let capturedOnAlert: (() => void) | undefined;
vi.mock("@/lib/queries/alerts", () => ({
  fetchAlerts: (filters: unknown) => fetchAlerts(filters),
}));
vi.mock("@/lib/queries/instruments", () => ({
  fetchInstrumentsById: () => fetchInstrumentsById(),
}));
vi.mock("@/lib/use-alerts-stream", () => ({
  useAlertsStream: (onAlert: () => void) => {
    capturedOnAlert = onAlert;
    return "open";
  },
}));

import { AlertsPageContent } from "./alerts-page-content";

function renderContent() {
  fetchAlerts.mockResolvedValue({ items: [], total: 0 });
  fetchInstrumentsById.mockResolvedValue(new Map());
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={queryClient}>
      <AlertsPageContent />
    </QueryClientProvider>,
  );
  return { ...view, queryClient };
}

describe("AlertsPageContent", () => {
  it("shows the empty state when there are no alerts", async () => {
    renderContent();

    await waitFor(() => expect(screen.getByText("No alerts yet.")).toBeInTheDocument());
  });

  it("shows a distinct error when alerts fail to load", async () => {
    fetchInstrumentsById.mockResolvedValue(new Map());
    fetchAlerts.mockRejectedValueOnce(new Error("network down"));
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <AlertsPageContent />
      </QueryClientProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByText("Couldn't load alerts. Check that the API is reachable and retry."),
      ).toBeInTheDocument(),
    );
  });

  it("shows the live connection indicator", async () => {
    renderContent();

    await waitFor(() => expect(screen.getByText("Live")).toBeInTheDocument());
  });

  it("invalidates the alerts list when a live alert is pushed, so the table reflects it", async () => {
    const { queryClient } = renderContent();
    await waitFor(() => expect(screen.getByText("No alerts yet.")).toBeInTheDocument());
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    capturedOnAlert?.();

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["alerts"] });
  });
});
