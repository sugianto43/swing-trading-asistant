import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { BehaviorEntry } from "@/lib/queries/performance";

// BehaviorEntryOut only carries position_id, no symbol, and there is no
// bulk by-id instrument lookup — link out to the position's own detail
// page instead of adding another join query for a table that's already
// one hop away from the symbol it would show.
export function BehaviorTable({ entries }: { entries: BehaviorEntry[] }) {
  if (entries.length === 0) {
    return <p className="p-6 text-center text-sm text-muted-foreground">No closed positions yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Position</TableHead>
          <TableHead>Stop Violated</TableHead>
          <TableHead className="text-right">Entry Deviation</TableHead>
          <TableHead className="text-right">Quantity Deviation</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry) => (
          <TableRow key={entry.position_id}>
            <TableCell className="font-medium">
              <Link href={`/positions/${entry.position_id}`} className="hover:underline">
                {entry.position_id}
              </Link>
            </TableCell>
            <TableCell>
              {entry.stop_violated === null ? (
                "—"
              ) : (
                <Badge variant={entry.stop_violated ? "destructive" : "secondary"}>
                  {entry.stop_violated ? "Yes" : "No"}
                </Badge>
              )}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {entry.entry_deviation_pct !== null ? `${entry.entry_deviation_pct.toFixed(1)}%` : "—"}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {entry.quantity_deviation_pct !== null
                ? `${entry.quantity_deviation_pct.toFixed(1)}%`
                : "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
