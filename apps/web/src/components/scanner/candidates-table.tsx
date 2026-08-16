"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { buildPlanHref } from "@/lib/queries/build-plan-href";
import type { ScanCandidate } from "@/lib/queries/scanner";

export function CandidatesTable({ candidates }: { candidates: ScanCandidate[] }) {
  if (candidates.length === 0) {
    return (
      <p className="p-6 text-center text-sm text-muted-foreground">
        No candidates match these filters.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Setup</TableHead>
          <TableHead className="text-right">Score</TableHead>
          <TableHead className="text-right">Momentum</TableHead>
          <TableHead className="text-right">Risk/Reward</TableHead>
          <TableHead>Scan Date</TableHead>
          <TableHead />
        </TableRow>
      </TableHeader>
      <TableBody>
        {candidates.map((candidate) => (
          <TableRow key={`${candidate.symbol}-${candidate.scan_date}-${candidate.setup_type}`}>
            <TableCell className="font-medium">
              <Link href={`/instruments/${candidate.symbol}`} className="hover:underline">
                {candidate.symbol}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant="outline">{candidate.setup_type}</Badge>
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {candidate.composite_score.toFixed(1)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {candidate.momentum_score.toFixed(1)}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {candidate.risk_reward_score.toFixed(1)}
            </TableCell>
            <TableCell className="text-muted-foreground">{candidate.scan_date}</TableCell>
            <TableCell>
              <Link href={buildPlanHref(candidate)} className="text-sm text-primary hover:underline">
                Build plan
              </Link>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
