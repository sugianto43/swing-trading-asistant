import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import { fetchSectorPerformance } from "./sector-performance";

describe("fetchSectorPerformance", () => {
  it("passes as_of through as a required query param", async () => {
    getMock.mockResolvedValueOnce({ data: [], error: undefined });

    await fetchSectorPerformance("2024-03-01");

    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/intelligence/sector-performance",
      expect.objectContaining({ params: { query: { as_of: "2024-03-01" } } }),
    );
  });

  it("returns an empty list rather than throwing when no sectors qualify", async () => {
    getMock.mockResolvedValueOnce({ data: [], error: undefined });

    await expect(fetchSectorPerformance("2024-03-01")).resolves.toEqual([]);
  });

  it("throws on a failed request", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchSectorPerformance("2024-03-01")).rejects.toThrow(
      "sector performance request failed",
    );
  });
});
