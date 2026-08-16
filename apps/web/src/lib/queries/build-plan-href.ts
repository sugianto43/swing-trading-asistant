import type { ScanCandidate } from "@/lib/queries/scanner";

export function buildPlanHref(candidate: ScanCandidate): string {
  const params = new URLSearchParams({
    symbol: candidate.symbol,
    setup: candidate.setup_type,
    date: candidate.scan_date,
  });
  return `/risk?${params.toString()}`;
}
