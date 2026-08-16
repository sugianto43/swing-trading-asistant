import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type TradePlan = components["schemas"]["TradePlanOut"];
export type TradePlanCreate = components["schemas"]["TradePlanCreate"];
export type TradePlanStatus = components["schemas"]["TradePlanStatus"];

export interface TradePlanFilters {
  symbol?: string;
  setupType?: TradePlanCreate["setup_type"];
  status?: TradePlanStatus;
  planDate?: string;
  page?: number;
}

const PAGE_SIZE = 50;

/** VALID and REJECTED are both normal (HTTP 201) results — the backend
 * never fails a request just because a plan didn't qualify. This throws
 * only for a genuine request failure (network/validation/5xx), never for
 * a REJECTED plan, which callers must render as a real result. */
export async function createTradePlan(payload: TradePlanCreate): Promise<TradePlan> {
  const { data, error } = await apiClient.POST("/api/v1/risk/trade-plans", { body: payload });
  if (error || !data) throw new Error("trade plan request failed");
  return data;
}

export async function fetchTradePlans(
  filters: TradePlanFilters,
): Promise<{ items: TradePlan[]; total: number }> {
  const { data, error } = await apiClient.GET("/api/v1/risk/trade-plans", {
    params: {
      query: {
        symbol: filters.symbol || undefined,
        setup_type: filters.setupType,
        status: filters.status,
        plan_date: filters.planDate,
        page: filters.page ?? 1,
        page_size: PAGE_SIZE,
      },
    },
  });
  if (error || !data) throw new Error("trade plans request failed");
  return { items: data.items, total: data.total };
}

export async function fetchTradePlan(id: string): Promise<TradePlan> {
  const { data, error, response } = await apiClient.GET("/api/v1/risk/trade-plans/{trade_plan_id}", {
    params: { path: { trade_plan_id: id } },
  });
  if (response.status === 404) throw new Error("NOT_FOUND");
  if (error || !data) throw new Error("trade plan request failed");
  return data;
}
