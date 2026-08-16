import { EquityCurveChart } from "@/components/positions/equity-curve-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { fetchPerformanceSummary } from "@/lib/queries/performance";

// See fetchPerformanceSummary's own comment: no named PerformanceSummary
// annotation here either, for the same equity_curve tuple-widening reason.
type Summary = Awaited<ReturnType<typeof fetchPerformanceSummary>>;

export function PerformanceSummary({ summary }: { summary: Summary }) {
  const stats = [
    { label: "Total Realized P&L", value: summary.total_realized_pnl },
    { label: "Unrealized P&L", value: summary.unrealized_pnl },
    { label: "Exposure", value: summary.exposure },
    { label: "Closed Positions", value: summary.closed_position_count },
    { label: "Win Rate", value: `${summary.win_rate_pct.toFixed(1)}%` },
    { label: "Avg Win", value: summary.avg_win ?? "—" },
    { label: "Avg Loss", value: summary.avg_loss ?? "—" },
    { label: "Expectancy", value: summary.expectancy ?? "—" },
    { label: "Profit Factor", value: summary.profit_factor ?? "—" },
    { label: "Max Drawdown", value: `${summary.max_drawdown_pct.toFixed(1)}%` },
    { label: "Sharpe Ratio", value: summary.sharpe_ratio ?? "—" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Performance Summary</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label}>
              <dt className="text-xs text-muted-foreground">{stat.label}</dt>
              <dd className="text-lg font-semibold font-mono tabular-nums">{stat.value}</dd>
            </div>
          ))}
        </dl>
        {/* Same tuple-widening quirk as the Summary type above — the
            runtime shape is genuinely [string, number][], just not typed
            that way after openapi-fetch's response-extraction utilities. */}
        <EquityCurveChart points={summary.equity_curve as [string, number][]} />
      </CardContent>
    </Card>
  );
}
