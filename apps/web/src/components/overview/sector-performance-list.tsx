import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SectorPerformance } from "@/lib/queries/sector-performance";

export function SectorPerformanceList({ sectors }: { sectors: SectorPerformance[] }) {
  if (sectors.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Sector Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No sector performance data for this date yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  const maxAbs = Math.max(...sectors.map((s) => Math.abs(s.avg_return_pct)), 0.01);
  const sorted = [...sectors].sort((a, b) => b.avg_return_pct - a.avg_return_pct);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sector Performance</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {sorted.map((sector) => {
          const isPositive = sector.avg_return_pct >= 0;
          const widthPct = (Math.abs(sector.avg_return_pct) / maxAbs) * 100;
          return (
            <div key={sector.sector} className="flex items-center gap-3 text-sm">
              <span className="w-32 shrink-0 truncate" title={sector.sector}>
                {sector.sector}
              </span>
              <div className="relative h-4 flex-1 rounded bg-muted">
                <div
                  className={`absolute top-0 h-4 rounded ${
                    isPositive ? "bg-emerald-500" : "bg-destructive"
                  }`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
              <span
                className={`w-16 shrink-0 text-right tabular-nums ${
                  // text-emerald-600 measured 3.65:1 against white (axe,
                  // Phase 18) — below WCAG AA's 4.5:1 minimum for normal
                  // text; emerald-700 clears it while staying the same hue.
                  isPositive ? "text-emerald-700 dark:text-emerald-400" : "text-destructive"
                }`}
              >
                {isPositive ? "+" : ""}
                {sector.avg_return_pct.toFixed(2)}%
              </span>
              <span className="w-10 shrink-0 text-right text-xs text-muted-foreground">
                {sector.instrument_count}
              </span>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
