"use client";

import { useQuery } from "@tanstack/react-query";

import { JournalForm } from "@/components/positions/journal-form";
import { STATUS_BADGE_VARIANT } from "@/components/positions/position-status-badge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fetchInstrumentsById } from "@/lib/queries/instruments";
import { fetchExecutions, fetchJournal, fetchPosition } from "@/lib/queries/positions";

export function PositionDetailClient({ id }: { id: string }) {
  const positionQuery = useQuery({
    queryKey: ["position", id],
    queryFn: () => fetchPosition(id),
    retry: false,
  });
  const instrumentsQuery = useQuery({
    queryKey: ["instruments-by-id"],
    queryFn: fetchInstrumentsById,
    enabled: positionQuery.isSuccess,
  });
  const executionsQuery = useQuery({
    queryKey: ["executions", id],
    queryFn: () => fetchExecutions(id),
    enabled: positionQuery.isSuccess,
  });
  // A missing journal is a normal state (nobody has journaled this
  // position yet), not a fetch failure — fetchJournal resolves to null
  // rather than throwing, so this is a plain useQuery with no error branch
  // for the 404 case.
  const journalQuery = useQuery({
    queryKey: ["journal", id],
    queryFn: () => fetchJournal(id),
    enabled: positionQuery.isSuccess,
  });

  if (positionQuery.isPending) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const isNotFound = positionQuery.error?.message === "NOT_FOUND";

  if (isNotFound) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">No position found for &quot;{id}&quot;.</p>
      </div>
    );
  }

  if (positionQuery.isError || !positionQuery.data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">Couldn&apos;t load this position.</p>
        <p className="text-sm text-muted-foreground">Check that the API is reachable and retry.</p>
      </div>
    );
  }

  const position = positionQuery.data;
  const symbol = instrumentsQuery.isError
    ? position.instrument_id
    : (instrumentsQuery.data?.get(position.instrument_id)?.symbol ?? position.instrument_id);

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{symbol}</CardTitle>
          <Badge variant={STATUS_BADGE_VARIANT[position.status]}>{position.status}</Badge>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground">Quantity open</dt>
              <dd className="text-lg font-semibold tabular-nums">{position.quantity_open}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Avg entry price</dt>
              <dd className="text-lg font-semibold tabular-nums">
                {position.avg_entry_price ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Realized P&L</dt>
              <dd className="text-lg font-semibold tabular-nums">{position.realized_pnl}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Cumulative fees</dt>
              <dd className="text-lg font-semibold tabular-nums">
                {position.cumulative_entry_fees + position.cumulative_exit_fees}
              </dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-muted-foreground">
            opened={position.opened_at ?? "—"} closed={position.closed_at ?? "—"}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Executions</CardTitle>
        </CardHeader>
        <CardContent>
          {executionsQuery.isPending ? (
            <Skeleton className="h-24 w-full" />
          ) : executionsQuery.isError ? (
            <p className="text-sm text-muted-foreground">Couldn&apos;t load execution history.</p>
          ) : executionsQuery.data.length === 0 ? (
            <p className="text-sm text-muted-foreground">No executions recorded yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Side</TableHead>
                  <TableHead className="text-right">Quantity</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead className="text-right">Fee</TableHead>
                  <TableHead>Executed at</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {executionsQuery.data.map((execution) => (
                  <TableRow key={execution.id}>
                    <TableCell>
                      <Badge variant={execution.side === "BUY" ? "secondary" : "outline"}>
                        {execution.side}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{execution.quantity}</TableCell>
                    <TableCell className="text-right tabular-nums">{execution.price}</TableCell>
                    <TableCell className="text-right tabular-nums">{execution.fee}</TableCell>
                    <TableCell className="text-muted-foreground">{execution.executed_at}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Journal</CardTitle>
        </CardHeader>
        <CardContent>
          {journalQuery.isPending ? (
            <Skeleton className="h-48 w-full" />
          ) : journalQuery.isError ? (
            <p className="text-sm text-muted-foreground">Couldn&apos;t load the journal entry.</p>
          ) : (
            <JournalForm positionId={id} journal={journalQuery.data ?? null} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
