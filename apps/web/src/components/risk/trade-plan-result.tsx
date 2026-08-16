import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TradePlan } from "@/lib/queries/risk";

/** Both VALID and REJECTED are normal results the backend actually
 * returned — this renders whichever one it is, never treating REJECTED
 * as an error to apologize for. */
export function TradePlanResult({
  plan,
  symbol,
  linkToDetail = true,
}: {
  plan: TradePlan;
  symbol: string;
  /** False when already rendered on the plan's own detail page — linking
   * to /risk/{id} from there would be a self-referential dead link. */
  linkToDetail?: boolean;
}) {
  if (plan.status === "REJECTED") {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{symbol}: plan rejected</CardTitle>
          <Badge variant="destructive">REJECTED</Badge>
        </CardHeader>
        <CardContent>
          <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
            {plan.rejection_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    );
  }

  const stats = [
    { label: "Entry", value: plan.entry_price },
    { label: "Stop", value: plan.stop_price },
    { label: "Quantity", value: plan.quantity },
    { label: "Allocation", value: `${plan.allocation_pct.toFixed(1)}%` },
    { label: "Max Loss", value: plan.max_loss_amount },
    { label: "Risk/Reward", value: plan.risk_reward_ratio?.toFixed(2) ?? "—" },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>
          {linkToDetail ? (
            <Link href={`/risk/${plan.id}`} className="hover:underline">
              {symbol}: plan ready
            </Link>
          ) : (
            `${symbol}: plan ready`
          )}
        </CardTitle>
        <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
          VALID
        </Badge>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label}>
              <dt className="text-xs text-muted-foreground">{stat.label}</dt>
              <dd className="text-lg font-semibold tabular-nums">{stat.value}</dd>
            </div>
          ))}
        </dl>
        {plan.target_prices.length > 0 && (
          <p className="mt-3 text-sm text-muted-foreground">
            Targets: {plan.target_prices.join(", ")}
          </p>
        )}
        <Link
          href={`/positions?symbol=${symbol}&trade_plan_id=${plan.id}`}
          className="mt-3 inline-block text-sm text-primary hover:underline"
        >
          Record execution →
        </Link>
      </CardContent>
    </Card>
  );
}
