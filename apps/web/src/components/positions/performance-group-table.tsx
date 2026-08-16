import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { GroupPerformance } from "@/lib/queries/performance";

export function PerformanceGroupTable({
  title,
  groups,
  keyLabel,
}: {
  title: string;
  groups: GroupPerformance[];
  keyLabel: string;
}) {
  return (
    <div>
      <h2 className="mb-2 text-sm font-medium text-muted-foreground">{title}</h2>
      {groups.length === 0 ? (
        <p className="p-6 text-center text-sm text-muted-foreground">No closed positions yet.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{keyLabel}</TableHead>
              <TableHead className="text-right">Closed</TableHead>
              <TableHead className="text-right">Realized P&L</TableHead>
              <TableHead className="text-right">Win Rate</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groups.map((group) => (
              <TableRow key={group.key ?? "unknown"}>
                <TableCell className="font-medium">{group.key ?? "—"}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">{group.closed_position_count}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">{group.total_realized_pnl}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">
                  {group.win_rate_pct.toFixed(1)}%
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
