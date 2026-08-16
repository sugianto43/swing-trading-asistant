import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type PerformanceSummary = components["schemas"]["PerformanceSummaryOut"];
export type GroupPerformance = components["schemas"]["GroupPerformanceOut"];
export type BehaviorEntry = components["schemas"]["BehaviorEntryOut"];

// No explicit Promise<PerformanceSummary> return-type annotation: openapi-fetch's
// tuple type for equity_curve ([string, number][]) loses its tuple-ness when
// routed through the response-extraction utility types, and structurally
// comparing that widened array type against the named PerformanceSummary type
// fails even though the runtime shape is identical. Letting TS infer the
// return type sidesteps the false-positive mismatch; PerformanceSummary is
// still exported for callers that need to name the type.
export async function fetchPerformanceSummary() {
  const { data, error } = await apiClient.GET("/api/v1/performance/summary", {});
  if (error || !data) throw new Error("performance summary request failed");
  return data;
}

export async function fetchPerformanceBySetup(): Promise<GroupPerformance[]> {
  const { data, error } = await apiClient.GET("/api/v1/performance/by-setup", {});
  if (error || !data) throw new Error("performance by-setup request failed");
  return data;
}

export async function fetchPerformanceBySector(): Promise<GroupPerformance[]> {
  const { data, error } = await apiClient.GET("/api/v1/performance/by-sector", {});
  if (error || !data) throw new Error("performance by-sector request failed");
  return data;
}

export async function fetchPerformanceByHoldingPeriod(): Promise<GroupPerformance[]> {
  const { data, error } = await apiClient.GET("/api/v1/performance/by-holding-period", {});
  if (error || !data) throw new Error("performance by-holding-period request failed");
  return data;
}

export async function fetchPerformanceByScoreBucket(): Promise<GroupPerformance[]> {
  const { data, error } = await apiClient.GET("/api/v1/performance/by-score-bucket", {});
  if (error || !data) throw new Error("performance by-score-bucket request failed");
  return data;
}

export async function fetchPerformanceBehavior(): Promise<BehaviorEntry[]> {
  const { data, error } = await apiClient.GET("/api/v1/performance/behavior", {});
  if (error || !data) throw new Error("performance behavior request failed");
  return data;
}
