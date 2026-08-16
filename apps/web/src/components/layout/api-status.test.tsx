import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import { ApiStatus } from "./api-status";

function renderWithClient() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ApiStatus />
    </QueryClientProvider>,
  );
}

describe("ApiStatus", () => {
  it("shows a pending state before the health check resolves", () => {
    getMock.mockImplementationOnce(() => new Promise(() => {})); // never resolves
    renderWithClient();

    expect(screen.getByRole("status")).toHaveTextContent("Checking API…");
  });

  it("shows connected once the health check succeeds", async () => {
    getMock.mockResolvedValueOnce({ data: {}, error: undefined });
    renderWithClient();

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("API: connected"));
  });

  it("shows disconnected when the health check returns an error envelope", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "down" } });
    renderWithClient();

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("API: disconnected"));
  });

  it("shows disconnected when the health check request itself fails", async () => {
    getMock.mockRejectedValueOnce(new Error("network down"));
    renderWithClient();

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("API: disconnected"));
  });
});
