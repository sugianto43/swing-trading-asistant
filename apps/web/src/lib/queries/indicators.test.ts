import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import { fetchRecentIndicators } from "./indicators";

describe("fetchRecentIndicators", () => {
  it("reverses newest-first API order into chronological order", async () => {
    const items = [
      { trade_date: "2024-01-02", sma_20: 101 },
      { trade_date: "2024-01-01", sma_20: 100 },
    ];
    getMock.mockResolvedValueOnce({ data: { items, total: 2 }, error: undefined });

    const result = await fetchRecentIndicators("BBCA");

    expect(result.map((i) => i.trade_date)).toEqual(["2024-01-01", "2024-01-02"]);
  });

  it("throws rather than returning fabricated indicator data on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchRecentIndicators("BBCA")).rejects.toThrow("indicators request failed");
  });

  it("slices to the trailing 180 days, matching fetchRecentPriceBars' window", async () => {
    // Regression test: indicators and price bars feed the same chart and
    // must cover the same date range, or SMA lines can extend beyond
    // the candlestick series.
    const items = Array.from({ length: 200 }, (_, i) => ({
      trade_date: `day-${199 - i}`,
      sma_20: i,
    }));
    getMock.mockResolvedValueOnce({ data: { items, total: 200 }, error: undefined });

    const result = await fetchRecentIndicators("BBCA");

    expect(result).toHaveLength(180);
    expect(result[0].trade_date).toBe("day-20");
    expect(result[result.length - 1].trade_date).toBe("day-199");
  });
});
