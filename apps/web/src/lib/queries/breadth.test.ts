import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import { fetchLatestBreadth } from "./breadth";

describe("fetchLatestBreadth", () => {
  it("returns the snapshot on success", async () => {
    const snapshot = { id: "1", universe_size: 10 };
    getMock.mockResolvedValueOnce({ data: snapshot, error: undefined, response: { status: 200 } });

    await expect(fetchLatestBreadth()).resolves.toEqual(snapshot);
  });

  it("throws NOT_FOUND when no snapshot has been computed yet", async () => {
    getMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "no breadth snapshot available" },
      response: { status: 404 },
    });

    await expect(fetchLatestBreadth()).rejects.toThrow("NOT_FOUND");
  });

  it("throws on any other failure without fabricating data", async () => {
    getMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "boom" },
      response: { status: 500 },
    });

    await expect(fetchLatestBreadth()).rejects.toThrow("breadth request failed");
  });
});
