import { Badge } from "@/components/ui/badge";
import type { Instrument } from "@/lib/queries/instruments";

// SUSPENDED (temporarily halted) and DELISTED (permanently removed) are
// distinct lifecycle states, not variations of the same thing — shown
// with different badge styling rather than collapsing both into a
// single "not ACTIVE" red badge.
const STATUS_VARIANT: Record<Instrument["status"], "secondary" | "outline" | "destructive"> = {
  ACTIVE: "secondary",
  SUSPENDED: "outline",
  DELISTED: "destructive",
};

export function InstrumentHeader({ instrument }: { instrument: Instrument }) {
  return (
    <div className="flex flex-wrap items-baseline gap-3">
      <h1 className="text-2xl font-semibold tracking-tight">{instrument.symbol}</h1>
      <span className="text-muted-foreground">{instrument.company_name}</span>
      {instrument.sector && <Badge variant="outline">{instrument.sector}</Badge>}
      <Badge variant={STATUS_VARIANT[instrument.status]}>{instrument.status}</Badge>
    </div>
  );
}
