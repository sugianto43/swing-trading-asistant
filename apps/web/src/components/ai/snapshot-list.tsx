import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Instrument } from "@/lib/queries/instruments";
import type { AnalysisSnapshot } from "@/lib/queries/ai";

const QUESTION_PREVIEW_LENGTH = 80;

function previewQuestion(question: string): string {
  return question.length > QUESTION_PREVIEW_LENGTH
    ? `${question.slice(0, QUESTION_PREVIEW_LENGTH)}…`
    : question;
}

export function SnapshotList({
  snapshots,
  instrumentsById,
}: {
  snapshots: AnalysisSnapshot[];
  instrumentsById: Map<string, Instrument>;
}) {
  if (snapshots.length === 0) {
    return <p className="p-6 text-center text-sm text-muted-foreground">No analyses yet.</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Question</TableHead>
          <TableHead>Flags</TableHead>
          <TableHead>Asked</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {snapshots.map((snapshot) => (
          <TableRow key={snapshot.id}>
            <TableCell className="font-medium">
              <Link href={`/ai/${snapshot.id}`} className="hover:underline">
                {(snapshot.instrument_id && instrumentsById.get(snapshot.instrument_id)?.symbol) ?? "—"}
              </Link>
            </TableCell>
            <TableCell className="text-sm">{previewQuestion(snapshot.question)}</TableCell>
            <TableCell>
              {snapshot.guardrail_flags.length > 0 ? (
                <Badge variant="destructive">{snapshot.guardrail_flags.length} flagged</Badge>
              ) : (
                <span className="text-xs text-muted-foreground">—</span>
              )}
            </TableCell>
            <TableCell className="text-muted-foreground">{snapshot.created_at}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
