import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { CHART_LOOKBACK_DAYS } from "@/lib/queries/chart-constants";

export type Instrument = components["schemas"]["InstrumentOut"];
export type PriceBar = components["schemas"]["PriceBarOut"];

export async function fetchInstrument(symbol: string): Promise<Instrument> {
  const { data, error, response } = await apiClient.GET("/api/v1/instruments/{symbol}", {
    params: { path: { symbol } },
  });
  if (response.status === 404) throw new Error("NOT_FOUND");
  if (error || !data) throw new Error("instrument request failed");
  return data;
}

export async function fetchRecentPriceBars(symbol: string): Promise<PriceBar[]> {
  const { data, error } = await apiClient.GET("/api/v1/instruments/{symbol}/prices", {
    params: { path: { symbol }, query: { adjusted: true, page_size: 200 } },
  });
  if (error || !data) throw new Error("price bars request failed");
  // API returns newest-first; charts need chronological order, and only
  // the trailing window is useful for a swing-trading price chart.
  return [...data.items].reverse().slice(-CHART_LOOKBACK_DAYS);
}

/** TradePlanOut only carries instrument_id (uuid), not symbol, and there
 * is no GET /instruments/{id}-by-uuid endpoint — only by symbol. This is
 * the client-side join trade-plan screens need to show a symbol at all.
 * page_size 200 covers a personal-use universe in one request; a
 * paginated fetch-all isn't worth the complexity at this scale. */
export async function fetchInstrumentsById(): Promise<Map<string, Instrument>> {
  const { data, error } = await apiClient.GET("/api/v1/instruments", {
    params: { query: { page_size: 200 } },
  });
  if (error || !data) throw new Error("instruments request failed");
  return new Map(data.items.map((instrument) => [instrument.id, instrument]));
}
