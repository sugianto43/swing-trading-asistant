import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import { fetchInstrumentCandidates, fetchScanCandidates } from "./scanner";

describe("fetchScanCandidates", () => {
  it("defaults sort to score and page to 1", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchScanCandidates({});

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.sort).toBe("score");
    expect(options.params.query.page).toBe(1);
  });

  it("forwards setup/min-score/sort filters", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchScanCandidates({ setup: "BREAKOUT", minScore: 70, sort: "momentum", page: 2 });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query).toMatchObject({
      setup: "BREAKOUT",
      min_score: 70,
      sort: "momentum",
      page: 2,
    });
  });

  it("omits an empty sector string rather than sending sector=''", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchScanCandidates({ sector: "" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.sector).toBeUndefined();
  });

  it("throws rather than returning a fabricated empty result on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchScanCandidates({})).rejects.toThrow("scanner candidates request failed");
  });
});

describe("fetchInstrumentCandidates", () => {
  it("scopes the request to the given symbol", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchInstrumentCandidates("BBCA");

    expect(getMock).toHaveBeenCalledWith(
      "/api/v1/instruments/{symbol}/candidates",
      expect.objectContaining({ params: { path: { symbol: "BBCA" } } }),
    );
  });
});
