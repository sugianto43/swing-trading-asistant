import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import { fetchInstrument, fetchInstrumentsById, fetchRecentPriceBars } from "./instruments";

describe("fetchInstrument", () => {
  it("returns the instrument on success", async () => {
    const instrument = { symbol: "BBCA" };
    getMock.mockResolvedValueOnce({ data: instrument, error: undefined, response: { status: 200 } });

    await expect(fetchInstrument("BBCA")).resolves.toEqual(instrument);
  });

  it("throws NOT_FOUND for an unseeded symbol rather than a generic error", async () => {
    getMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "not found" },
      response: { status: 404 },
    });

    await expect(fetchInstrument("NOPE")).rejects.toThrow("NOT_FOUND");
  });
});

describe("fetchRecentPriceBars", () => {
  it("reverses newest-first API order into chronological order", async () => {
    const items = [
      { trade_date: "2024-01-03", close: 102 },
      { trade_date: "2024-01-02", close: 101 },
      { trade_date: "2024-01-01", close: 100 },
    ];
    getMock.mockResolvedValueOnce({ data: { items, total: 3 }, error: undefined });

    const result = await fetchRecentPriceBars("BBCA");

    expect(result.map((b) => b.trade_date)).toEqual(["2024-01-01", "2024-01-02", "2024-01-03"]);
  });

  it("requests adjusted prices", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchRecentPriceBars("BBCA");

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.adjusted).toBe(true);
  });

  it("throws rather than returning an empty chart on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchRecentPriceBars("BBCA")).rejects.toThrow("price bars request failed");
  });

  it("slices to the trailing 180 days when the API returns more, keeping the most recent", async () => {
    // Newest-first from the API, 200 items (the page_size requested).
    const items = Array.from({ length: 200 }, (_, i) => ({
      trade_date: `day-${199 - i}`, // day-199 (newest) ... day-0 (oldest)
      close: i,
    }));
    getMock.mockResolvedValueOnce({ data: { items, total: 200 }, error: undefined });

    const result = await fetchRecentPriceBars("BBCA");

    expect(result).toHaveLength(180);
    // Chronological order preserved, and it's the most recent 180 days
    // (day-20 through day-199), not the oldest 180.
    expect(result[0].trade_date).toBe("day-20");
    expect(result[result.length - 1].trade_date).toBe("day-199");
  });

  it("returns everything, unsliced, when the API returns fewer than 180 bars", async () => {
    const items = [
      { trade_date: "2024-01-02", close: 101 },
      { trade_date: "2024-01-01", close: 100 },
    ];
    getMock.mockResolvedValueOnce({ data: { items, total: 2 }, error: undefined });

    const result = await fetchRecentPriceBars("BBCA");

    expect(result).toHaveLength(2);
  });
});

describe("fetchInstrumentsById", () => {
  it("keys instruments by id for a client-side join against instrument_id-only records", async () => {
    const items = [
      { id: "uuid-1", symbol: "BBCA" },
      { id: "uuid-2", symbol: "TLKM" },
    ];
    getMock.mockResolvedValueOnce({ data: { items, total: 2 }, error: undefined });

    const result = await fetchInstrumentsById();

    expect(result.get("uuid-1")).toEqual(items[0]);
    expect(result.get("uuid-2")).toEqual(items[1]);
    expect(result.get("unknown-uuid")).toBeUndefined();
  });

  it("throws rather than returning an empty map on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchInstrumentsById()).rejects.toThrow("instruments request failed");
  });
});
