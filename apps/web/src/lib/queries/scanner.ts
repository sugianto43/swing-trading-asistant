import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ScanCandidate = components["schemas"]["ScanCandidateOut"];
export type SetupType = components["schemas"]["SetupType"];
export type ScannerSort = "score" | "momentum" | "risk_reward" | "volume_score";

export interface ScannerFilters {
  sector?: string;
  setup?: SetupType;
  minScore?: number;
  sort?: ScannerSort;
  page?: number;
}

const PAGE_SIZE = 50;

export async function fetchScanCandidates(filters: ScannerFilters): Promise<{
  items: ScanCandidate[];
  total: number;
}> {
  const { data, error } = await apiClient.GET("/api/v1/scanner/candidates", {
    params: {
      query: {
        sector: filters.sector || undefined,
        setup: filters.setup,
        min_score: filters.minScore,
        sort: filters.sort ?? "score",
        page: filters.page ?? 1,
        page_size: PAGE_SIZE,
      },
    },
  });
  if (error || !data) throw new Error("scanner candidates request failed");
  return { items: data.items, total: data.total };
}

export async function fetchInstrumentCandidates(symbol: string): Promise<ScanCandidate[]> {
  const { data, error } = await apiClient.GET("/api/v1/instruments/{symbol}/candidates", {
    params: { path: { symbol } },
  });
  if (error || !data) throw new Error("instrument candidates request failed");
  return data.items;
}
