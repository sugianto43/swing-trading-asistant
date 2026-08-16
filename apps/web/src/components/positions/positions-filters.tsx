"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { PositionFilters, PositionStatus } from "@/lib/queries/positions";

const STATUSES: PositionStatus[] = ["PLANNED", "OPEN", "PARTIALLY_CLOSED", "CLOSED", "CANCELLED"];
const ALL_STATUSES = "__all__";

export function PositionsFiltersBar({
  filters,
  onChange,
}: {
  filters: PositionFilters;
  onChange: (next: PositionFilters) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Input
        type="text"
        placeholder="Symbol"
        aria-label="Symbol filter"
        className="w-40"
        value={filters.symbol ?? ""}
        onChange={(e) => onChange({ ...filters, symbol: e.target.value, page: 1 })}
      />

      <Select
        value={filters.status ?? ALL_STATUSES}
        onValueChange={(value) =>
          onChange({
            ...filters,
            status: value === ALL_STATUSES ? undefined : (value as PositionStatus),
            page: 1,
          })
        }
      >
        <SelectTrigger aria-label="Status" className="w-48">
          <SelectValue placeholder="All statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_STATUSES}>All statuses</SelectItem>
          {STATUSES.map((status) => (
            <SelectItem key={status} value={status}>
              {status}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
