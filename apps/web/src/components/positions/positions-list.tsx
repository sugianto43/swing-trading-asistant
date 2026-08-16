import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { STATUS_BADGE_VARIANT } from "@/components/positions/position-status-badge";
import type { Instrument } from "@/lib/queries/instruments";
import type { Position } from "@/lib/queries/positions";

export function PositionsList({
  positions,
  instrumentsById,
}: {
  positions: Position[];
  instrumentsById: Map<string, Instrument>;
}) {
  if (positions.length === 0) {
    return <p className="p-6 text-center text-sm text-muted-foreground">No positions yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Quantity Open</TableHead>
          <TableHead className="text-right">Avg Entry</TableHead>
          <TableHead className="text-right">Realized P&L</TableHead>
          <TableHead>Opened</TableHead>
          <TableHead>Closed</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {positions.map((position) => (
          <TableRow key={position.id}>
            <TableCell className="font-medium">
              <Link href={`/positions/${position.id}`} className="hover:underline">
                {instrumentsById.get(position.instrument_id)?.symbol ?? "—"}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_BADGE_VARIANT[position.status]}>{position.status}</Badge>
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">{position.quantity_open}</TableCell>
            <TableCell className="text-right font-mono tabular-nums">
              {position.avg_entry_price ?? "—"}
            </TableCell>
            <TableCell className="text-right font-mono tabular-nums">{position.realized_pnl}</TableCell>
            <TableCell className="text-muted-foreground">{position.opened_at ?? "—"}</TableCell>
            <TableCell className="text-muted-foreground">{position.closed_at ?? "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
