import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
const postMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: (...args: unknown[]) => postMock(...args),
  },
}));

import { createTradePlan, fetchTradePlan, fetchTradePlans } from "./risk";

const PAYLOAD = {
  symbol: "BBCA",
  setup_type: "BREAKOUT" as const,
  plan_date: "2024-03-01",
  capital: 100_000_000,
};

describe("createTradePlan", () => {
  it("returns a VALID plan as a normal result, not an error", async () => {
    const plan = { id: "1", status: "VALID", rejection_reasons: [] };
    postMock.mockResolvedValueOnce({ data: plan, error: undefined });

    await expect(createTradePlan(PAYLOAD)).resolves.toEqual(plan);
  });

  it("returns a REJECTED plan as a normal result too — rejection is data, not a failure", async () => {
    const plan = { id: "2", status: "REJECTED", rejection_reasons: ["no qualifying candidate"] };
    postMock.mockResolvedValueOnce({ data: plan, error: undefined });

    const result = await createTradePlan(PAYLOAD);
    expect(result.status).toBe("REJECTED");
  });

  it("throws only on a genuine request failure", async () => {
    postMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(createTradePlan(PAYLOAD)).rejects.toThrow("trade plan request failed");
  });
});

describe("fetchTradePlans", () => {
  it("defaults to page 1 and omits an empty sector-style symbol filter", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchTradePlans({ symbol: "" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.symbol).toBeUndefined();
    expect(options.params.query.page).toBe(1);
  });

  it("forwards a real symbol value, not just dropping it like the empty-string case", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchTradePlans({ symbol: "BBCA" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.symbol).toBe("BBCA");
  });

  it("forwards status/setup/date filters", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchTradePlans({ status: "REJECTED", setupType: "BREAKOUT", planDate: "2024-03-01" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query).toMatchObject({
      status: "REJECTED",
      setup_type: "BREAKOUT",
      plan_date: "2024-03-01",
    });
  });

  it("throws rather than returning a fabricated empty result on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchTradePlans({})).rejects.toThrow("trade plans request failed");
  });
});

describe("fetchTradePlan", () => {
  it("returns the plan on success", async () => {
    const plan = { id: "1", status: "VALID" };
    getMock.mockResolvedValueOnce({ data: plan, error: undefined, response: { status: 200 } });

    await expect(fetchTradePlan("1")).resolves.toEqual(plan);
  });

  it("throws NOT_FOUND for an unknown id, distinct from a generic failure", async () => {
    getMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "trade plan not found" },
      response: { status: 404 },
    });

    await expect(fetchTradePlan("nope")).rejects.toThrow("NOT_FOUND");
  });
});
