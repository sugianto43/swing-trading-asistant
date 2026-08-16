import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SectorPerformance = components["schemas"]["SectorPerformanceOut"];

/** as_of is required by the backend (no default) — callers must always
 * supply one. Prefer a date already known to have data (e.g. the latest
 * breadth snapshot's as_of) over "today", which commonly has none yet. */
export async function fetchSectorPerformance(asOf: string): Promise<SectorPerformance[]> {
  const { data, error } = await apiClient.GET("/api/v1/intelligence/sector-performance", {
    params: { query: { as_of: asOf } },
  });
  if (error || !data) throw new Error("sector performance request failed");
  return data;
}
