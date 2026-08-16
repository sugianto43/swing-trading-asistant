import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Alert = components["schemas"]["AlertOut"];
export type AlertType = components["schemas"]["AlertType"];

export interface AlertFilters {
  alertType?: AlertType;
  symbol?: string;
  triggerDate?: string;
  page?: number;
}

const PAGE_SIZE = 50;

export async function fetchAlerts(filters: AlertFilters): Promise<{ items: Alert[]; total: number }> {
  const { data, error } = await apiClient.GET("/api/v1/alerts", {
    params: {
      query: {
        alert_type: filters.alertType,
        symbol: filters.symbol || undefined,
        trigger_date: filters.triggerDate || undefined,
        page: filters.page ?? 1,
        page_size: PAGE_SIZE,
      },
    },
  });
  if (error || !data) throw new Error("alerts request failed");
  return { items: data.items, total: data.total };
}
