import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import { fetchAlerts } from "./alerts";

describe("fetchAlerts", () => {
  it("defaults to page 1 and omits an empty symbol/trigger_date filter", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchAlerts({ symbol: "", triggerDate: "" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.symbol).toBeUndefined();
    expect(options.params.query.trigger_date).toBeUndefined();
    expect(options.params.query.page).toBe(1);
  });

  it("forwards alert_type, symbol, and trigger_date filters", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchAlerts({ alertType: "BREAKOUT", symbol: "BBCA", triggerDate: "2024-03-01" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query).toMatchObject({
      alert_type: "BREAKOUT",
      symbol: "BBCA",
      trigger_date: "2024-03-01",
    });
  });

  it("throws rather than returning a fabricated empty result on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchAlerts({})).rejects.toThrow("alerts request failed");
  });
});
