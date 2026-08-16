"use client";

import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ScannerFilters, ScannerSort, SetupType } from "@/lib/queries/scanner";

const SETUP_TYPES: SetupType[] = [
  "BREAKOUT",
  "PULLBACK_CONTINUATION",
  "MOMENTUM_CONTINUATION",
  "MA_RECLAIM",
  "VOLATILITY_SQUEEZE",
];

const SORT_OPTIONS: { value: ScannerSort; label: string }[] = [
  { value: "score", label: "Composite Score" },
  { value: "momentum", label: "Momentum" },
  { value: "risk_reward", label: "Risk/Reward" },
  { value: "volume_score", label: "Volume" },
];

const ALL_SETUPS = "__all__";

export function ScannerFiltersBar({
  filters,
  onChange,
}: {
  filters: ScannerFilters;
  onChange: (next: ScannerFilters) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select
        value={filters.setup ?? ALL_SETUPS}
        onValueChange={(value) =>
          onChange({ ...filters, setup: value === ALL_SETUPS ? undefined : (value as SetupType), page: 1 })
        }
      >
        <SelectTrigger aria-label="Setup type" className="w-48">
          <SelectValue placeholder="All setups" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_SETUPS}>All setups</SelectItem>
          {SETUP_TYPES.map((setup) => (
            <SelectItem key={setup} value={setup}>
              {setup}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        type="text"
        placeholder="Sector"
        aria-label="Sector"
        className="w-40"
        value={filters.sector ?? ""}
        onChange={(e) => onChange({ ...filters, sector: e.target.value, page: 1 })}
      />

      <Input
        type="number"
        placeholder="Min score"
        aria-label="Minimum score"
        className="w-32"
        value={filters.minScore ?? ""}
        onChange={(e) =>
          onChange({
            ...filters,
            minScore: e.target.value === "" ? undefined : Number(e.target.value),
            page: 1,
          })
        }
      />

      <Select
        value={filters.sort ?? "score"}
        onValueChange={(value) => onChange({ ...filters, sort: value as ScannerSort, page: 1 })}
      >
        <SelectTrigger aria-label="Sort by" className="w-48">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              Sort: {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
