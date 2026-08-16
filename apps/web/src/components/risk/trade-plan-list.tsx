import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Instrument } from "@/lib/queries/instruments";
import type { TradePlan } from "@/lib/queries/risk";

export function TradePlanList({
  plans,
  instrumentsById,
}: {
  plans: TradePlan[];
  instrumentsById: Map<string, Instrument>;
}) {
  if (plans.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-muted-foreground">No trade plans yet.</p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Setup</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Entry</TableHead>
          <TableHead className="text-right">Quantity</TableHead>
          <TableHead className="text-right">Allocation</TableHead>
          <TableHead>Plan Date</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {plans.map((plan) => (
          <TableRow key={plan.id}>
            <TableCell className="font-medium">
              <Link href={`/risk/${plan.id}`} className="hover:underline">
                {instrumentsById.get(plan.instrument_id)?.symbol ?? "—"}
              </Link>
            </TableCell>
            <TableCell>{plan.setup_type}</TableCell>
            <TableCell>
              <Badge variant={plan.status === "VALID" ? "secondary" : "destructive"}>
                {plan.status}
              </Badge>
            </TableCell>
            <TableCell className="text-right tabular-nums">{plan.entry_price ?? "—"}</TableCell>
            <TableCell className="text-right tabular-nums">{plan.quantity}</TableCell>
            <TableCell className="text-right tabular-nums">
              {plan.allocation_pct.toFixed(1)}%
            </TableCell>
            <TableCell className="text-muted-foreground">{plan.plan_date}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
