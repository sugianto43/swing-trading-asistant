import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BreadthSnapshot } from "@/lib/queries/breadth";

const REGIME_LABEL: Record<BreadthSnapshot["regime"], string> = {
  RISK_ON: "Risk On",
  RISK_OFF: "Risk Off",
  NEUTRAL: "Neutral",
};

function RegimeBadge({ regime }: { regime: BreadthSnapshot["regime"] }) {
  if (regime === "RISK_ON") {
    return (
      <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
        {REGIME_LABEL[regime]}
      </Badge>
    );
  }
  if (regime === "RISK_OFF") {
    return <Badge variant="destructive">{REGIME_LABEL[regime]}</Badge>;
  }
  return <Badge variant="secondary">{REGIME_LABEL[regime]}</Badge>;
}

function formatPct(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(1)}%`;
}

export function BreadthStats({ breadth }: { breadth: BreadthSnapshot }) {
  const stats = [
    { label: "Universe", value: breadth.universe_size.toString() },
    { label: "Advancers", value: breadth.advancers.toString() },
    { label: "Decliners", value: breadth.decliners.toString() },
    { label: "% Above SMA50", value: formatPct(breadth.pct_above_sma50) },
    { label: "% Above SMA200", value: formatPct(breadth.pct_above_sma200) },
    { label: "New 20d Highs", value: breadth.new_highs_20.toString() },
    { label: "New 20d Lows", value: breadth.new_lows_20.toString() },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Market Breadth</CardTitle>
        <RegimeBadge regime={breadth.regime} />
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          {stats.map((stat) => (
            <div key={stat.label}>
              <dt className="text-xs text-muted-foreground">{stat.label}</dt>
              <dd className="text-lg font-semibold font-mono tabular-nums">{stat.value}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-xs text-muted-foreground">As of {breadth.as_of}</p>
      </CardContent>
    </Card>
  );
}
