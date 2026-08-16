import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Execution = components["schemas"]["ExecutionOut"];
export type ExecutionCreate = components["schemas"]["ExecutionCreate"];
export type ExecutionSide = components["schemas"]["ExecutionSide"];
export type Position = components["schemas"]["PositionOut"];
export type PositionStatus = components["schemas"]["PositionStatus"];
export type Journal = components["schemas"]["JournalOut"];
export type JournalUpsert = components["schemas"]["JournalUpsert"];

export interface PositionFilters {
  symbol?: string;
  status?: PositionStatus;
  page?: number;
}

const PAGE_SIZE = 50;

/** A 404/409 here is a genuine request failure the form must surface
 * verbatim (overselling, unknown symbol) — unlike Phase 14's trade plans,
 * there is no VALID/REJECTED-as-both-normal-result duality for an
 * execution. Every successful POST is a real position update; anything
 * else is a real error. */
export async function recordExecution(payload: ExecutionCreate): Promise<Position> {
  const { data, error } = await apiClient.POST("/api/v1/executions", { body: payload });
  if (error || !data) throw new Error(errorDetail(error) ?? "execution request failed");
  return data;
}

export async function fetchExecutions(positionId: string): Promise<Execution[]> {
  const { data, error } = await apiClient.GET("/api/v1/executions", {
    params: { query: { position_id: positionId, page_size: PAGE_SIZE } },
  });
  if (error || !data) throw new Error("executions request failed");
  return data.items;
}

export async function fetchPositions(
  filters: PositionFilters,
): Promise<{ items: Position[]; total: number }> {
  const { data, error } = await apiClient.GET("/api/v1/positions", {
    params: {
      query: {
        symbol: filters.symbol || undefined,
        status: filters.status,
        page: filters.page ?? 1,
        page_size: PAGE_SIZE,
      },
    },
  });
  if (error || !data) throw new Error("positions request failed");
  return { items: data.items, total: data.total };
}

export async function fetchPosition(id: string): Promise<Position> {
  const { data, error, response } = await apiClient.GET("/api/v1/positions/{position_id}", {
    params: { path: { position_id: id } },
  });
  if (response.status === 404) throw new Error("NOT_FOUND");
  if (error || !data) throw new Error("position request failed");
  return data;
}

/** A missing journal is the normal state for a position nobody has
 * journaled yet — not an error to render a page-level failure for, unlike
 * fetchTradePlan's NOT_FOUND (a whole missing resource). Callers should
 * treat null as "show an empty journal form," not as a fetch failure. */
export async function fetchJournal(positionId: string): Promise<Journal | null> {
  const { data, error, response } = await apiClient.GET("/api/v1/positions/{position_id}/journal", {
    params: { path: { position_id: positionId } },
  });
  if (response.status === 404) return null;
  if (error || !data) throw new Error("journal request failed");
  return data;
}

export async function upsertJournal(positionId: string, payload: JournalUpsert): Promise<Journal> {
  const { data, error } = await apiClient.POST("/api/v1/positions/{position_id}/journal", {
    params: { path: { position_id: positionId } },
    body: payload,
  });
  if (error || !data) throw new Error("journal upsert failed");
  return data;
}

function errorDetail(error: unknown): string | undefined {
  if (error && typeof error === "object" && "detail" in error && typeof error.detail === "string") {
    return error.detail;
  }
  return undefined;
}
