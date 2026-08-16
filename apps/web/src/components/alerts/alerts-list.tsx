import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Instrument } from "@/lib/queries/instruments";
import type { Alert } from "@/lib/queries/alerts";

export function AlertsList({
  alerts,
  instrumentsById,
}: {
  alerts: Alert[];
  instrumentsById: Map<string, Instrument>;
}) {
  if (alerts.length === 0) {
    return <p className="p-6 text-center text-sm text-muted-foreground">No alerts yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Message</TableHead>
          <TableHead>Trigger Date</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {alerts.map((alert) => (
          <TableRow key={alert.id}>
            <TableCell className="font-medium">
              {instrumentsById.get(alert.instrument_id)?.symbol ?? "—"}
            </TableCell>
            <TableCell>
              <Badge variant="outline">{alert.alert_type}</Badge>
            </TableCell>
            <TableCell className="text-sm">{alert.message}</TableCell>
            <TableCell className="text-muted-foreground">{alert.trigger_date}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
