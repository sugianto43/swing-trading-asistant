import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: (...args: unknown[]) => getMock(...args) },
}));

import {
  fetchPerformanceBehavior,
  fetchPerformanceByHoldingPeriod,
  fetchPerformanceByScoreBucket,
  fetchPerformanceBySector,
  fetchPerformanceBySetup,
  fetchPerformanceSummary,
} from "./performance";

describe("performance queries", () => {
  it("fetchPerformanceSummary returns the summary on success", async () => {
    const summary = { initial_capital: 100, total_realized_pnl: 0, equity_curve: [] };
    getMock.mockResolvedValueOnce({ data: summary, error: undefined });

    await expect(fetchPerformanceSummary()).resolves.toEqual(summary);
  });

  it("fetchPerformanceSummary throws rather than fabricating a result on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchPerformanceSummary()).rejects.toThrow("performance summary request failed");
  });

  it.each([
    ["fetchPerformanceBySetup", fetchPerformanceBySetup],
    ["fetchPerformanceBySector", fetchPerformanceBySector],
    ["fetchPerformanceByHoldingPeriod", fetchPerformanceByHoldingPeriod],
    ["fetchPerformanceByScoreBucket", fetchPerformanceByScoreBucket],
  ] as const)("%s returns the group breakdown on success", async (_name, fn) => {
    const groups = [{ key: "BREAKOUT", closed_position_count: 2, total_realized_pnl: 100, win_rate_pct: 50 }];
    getMock.mockResolvedValueOnce({ data: groups, error: undefined });

    await expect(fn()).resolves.toEqual(groups);
  });

  it("fetchPerformanceBehavior returns behavior entries on success", async () => {
    const entries = [
      { position_id: "pos-1", stop_violated: true, entry_deviation_pct: 1.2, quantity_deviation_pct: 0 },
    ];
    getMock.mockResolvedValueOnce({ data: entries, error: undefined });

    await expect(fetchPerformanceBehavior()).resolves.toEqual(entries);
  });

  it("fetchPerformanceBehavior throws rather than returning a fabricated empty list", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchPerformanceBehavior()).rejects.toThrow("performance behavior request failed");
  });
});
