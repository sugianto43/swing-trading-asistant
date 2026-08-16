import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { STATUS_BADGE_VARIANT } from "@/components/positions/position-status-badge";
import type { Position } from "@/lib/queries/positions";

/** Every successful POST /executions is a real position update — there is
 * no VALID/REJECTED duality here like Phase 14's trade plans. Overselling
 * or an unknown symbol is a genuine error, rendered by the form itself via
 * mutation.isError, never routed through this component. */
export function ExecutionResult({ position, symbol }: { position: Position; symbol: string }) {
  const stats = [
    { label: "Quantity open", value: position.quantity_open },
    { label: "Avg entry price", value: position.avg_entry_price ?? "—" },
    { label: "Realized P&L", value: position.realized_pnl },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>
          <Link href={`/positions/${position.id}`} className="hover:underline">
            {symbol}: execution recorded
          </Link>
        </CardTitle>
        <Badge variant={STATUS_BADGE_VARIANT[position.status]}>{position.status}</Badge>
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
      </CardContent>
    </Card>
  );
}
