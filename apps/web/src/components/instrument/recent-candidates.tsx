import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buildPlanHref } from "@/lib/queries/build-plan-href";
import type { ScanCandidate } from "@/lib/queries/scanner";

export function RecentCandidates({ candidates }: { candidates: ScanCandidate[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Setups</CardTitle>
      </CardHeader>
      <CardContent>
        {candidates.length === 0 ? (
          <p className="text-sm text-muted-foreground">No scan candidates for this instrument yet.</p>
        ) : (
          <ul className="space-y-2">
            {candidates.map((candidate) => (
              <li
                key={`${candidate.scan_date}-${candidate.setup_type}`}
                className="flex items-center justify-between text-sm"
              >
                <span className="flex items-center gap-2">
                  <Badge variant="outline">{candidate.setup_type}</Badge>
                  <span className="text-muted-foreground">{candidate.scan_date}</span>
                </span>
                <span className="flex items-center gap-3">
                  <span className="tabular-nums">{candidate.composite_score.toFixed(1)}</span>
                  <Link href={buildPlanHref(candidate)} className="text-primary hover:underline">
                    Build plan
                  </Link>
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
