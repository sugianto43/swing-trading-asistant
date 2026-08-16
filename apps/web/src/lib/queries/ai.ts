import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type AnalysisSnapshot = components["schemas"]["AnalysisSnapshotOut"];
export type AnalyzeRequest = components["schemas"]["AnalyzeRequest"];

export interface SnapshotFilters {
  symbol?: string;
  page?: number;
}

const PAGE_SIZE = 50;

/** A 503 here means no LLM provider is configured (ADR-0003 — the
 * backend owns provider config, the UI never handles API keys) — a
 * genuine request failure to surface verbatim, the same discipline as
 * Phase 15's execution errors. There is no VALID/REJECTED-both-normal
 * duality here like Phase 14's trade plans. */
export async function analyzeQuestion(payload: AnalyzeRequest): Promise<AnalysisSnapshot> {
  const { data, error } = await apiClient.POST("/api/v1/ai/analyze", { body: payload });
  if (error || !data) throw new Error(errorDetail(error) ?? "analysis request failed");
  return data;
}

export async function fetchSnapshots(
  filters: SnapshotFilters,
): Promise<{ items: AnalysisSnapshot[]; total: number }> {
  const { data, error } = await apiClient.GET("/api/v1/ai/snapshots", {
    params: {
      query: {
        symbol: filters.symbol || undefined,
        page: filters.page ?? 1,
        page_size: PAGE_SIZE,
      },
    },
  });
  if (error || !data) throw new Error("snapshots request failed");
  return { items: data.items, total: data.total };
}

export async function fetchSnapshot(id: string): Promise<AnalysisSnapshot> {
  const { data, error, response } = await apiClient.GET("/api/v1/ai/snapshots/{snapshot_id}", {
    params: { path: { snapshot_id: id } },
  });
  if (response.status === 404) throw new Error("NOT_FOUND");
  if (error || !data) throw new Error("snapshot request failed");
  return data;
}

// app/errors.py's global exception handler wraps every error response —
// 404, 409, 503, all of them — in {"error": {"code", "message", "details"}},
// not FastAPI's bare default {"detail": "..."}. openapi-fetch's generated
// types don't reflect this (the OpenAPI schema is generated from each
// route's declared response models, which don't know about the app-wide
// exception handler), so this has to read the real runtime shape by hand.
function errorDetail(error: unknown): string | undefined {
  if (
    error &&
    typeof error === "object" &&
    "error" in error &&
    error.error &&
    typeof error.error === "object" &&
    "message" in error.error &&
    typeof error.error.message === "string"
  ) {
    return error.error.message;
  }
  return undefined;
}
