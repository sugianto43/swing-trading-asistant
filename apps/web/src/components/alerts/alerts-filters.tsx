"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { AlertFilters, AlertType } from "@/lib/queries/alerts";

const ALERT_TYPES: AlertType[] = [
  "SETUP_DETECTED",
  "BREAKOUT",
  "PRICE_NEAR_ENTRY",
  "PRICE_NEAR_STOP",
  "PRICE_NEAR_TARGET",
  "UNUSUAL_VOLUME",
  "STALE_DATA",
  "IMPORTANT_EVENT",
];

const ALL_TYPES = "__all__";

export function AlertsFiltersBar({
  filters,
  onChange,
}: {
  filters: AlertFilters;
  onChange: (next: AlertFilters) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select
        value={filters.alertType ?? ALL_TYPES}
        onValueChange={(value) =>
          onChange({
            ...filters,
            alertType: value === ALL_TYPES ? undefined : (value as AlertType),
            page: 1,
          })
        }
      >
        <SelectTrigger aria-label="Alert type" className="w-56">
          <SelectValue placeholder="All alert types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_TYPES}>All alert types</SelectItem>
          {ALERT_TYPES.map((type) => (
            <SelectItem key={type} value={type}>
              {type}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        type="text"
        placeholder="Symbol"
        aria-label="Symbol filter"
        className="w-40"
        value={filters.symbol ?? ""}
        onChange={(e) => onChange({ ...filters, symbol: e.target.value, page: 1 })}
      />

      <Input
        type="date"
        aria-label="Trigger date"
        className="w-40"
        value={filters.triggerDate ?? ""}
        onChange={(e) => onChange({ ...filters, triggerDate: e.target.value, page: 1 })}
      />
    </div>
  );
}
