import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type BreadthSnapshot = components["schemas"]["BreadthSnapshotOut"];

/** Throws NOT_FOUND when no breadth snapshot has been computed yet
 * (fresh install) — callers must render an explicit empty state, never
 * treat a missing snapshot as a fabricated zero/default one. */
export async function fetchLatestBreadth(): Promise<BreadthSnapshot> {
  const { data, error, response } = await apiClient.GET("/api/v1/intelligence/breadth");
  if (response.status === 404) throw new Error("NOT_FOUND");
  if (error || !data) throw new Error("breadth request failed");
  return data;
}
