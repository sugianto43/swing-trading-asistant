import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { CHART_LOOKBACK_DAYS } from "@/lib/queries/chart-constants";

export type IndicatorSnapshot = components["schemas"]["IndicatorSnapshotOut"];

export async function fetchRecentIndicators(symbol: string): Promise<IndicatorSnapshot[]> {
  const { data, error } = await apiClient.GET("/api/v1/instruments/{symbol}/indicators", {
    params: { path: { symbol }, query: { page_size: 200 } },
  });
  if (error || !data) throw new Error("indicators request failed");
  // API returns newest-first (matches price bars); charts need
  // chronological order, trimmed to the same trailing window as price
  // bars so the two series feeding PriceChart cover the same date range.
  return [...data.items].reverse().slice(-CHART_LOOKBACK_DAYS);
}
