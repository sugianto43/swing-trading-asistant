"use client";

import { useQuery } from "@tanstack/react-query";

import { TradePlanResult } from "@/components/risk/trade-plan-result";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchInstrumentsById } from "@/lib/queries/instruments";
import { fetchTradePlan } from "@/lib/queries/risk";

export function TradePlanDetailClient({ id }: { id: string }) {
  const planQuery = useQuery({
    queryKey: ["trade-plan", id],
    queryFn: () => fetchTradePlan(id),
    retry: false,
  });
  const instrumentsQuery = useQuery({
    queryKey: ["instruments-by-id"],
    queryFn: fetchInstrumentsById,
    enabled: planQuery.isSuccess,
  });

  if (planQuery.isPending) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const isNotFound = planQuery.error?.message === "NOT_FOUND";

  if (isNotFound) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">No trade plan found for &quot;{id}&quot;.</p>
      </div>
    );
  }

  if (planQuery.isError || !planQuery.data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">Couldn&apos;t load this trade plan.</p>
        <p className="text-sm text-muted-foreground">Check that the API is reachable and retry.</p>
      </div>
    );
  }

  const plan = planQuery.data;
  // A failed instrument lookup and a genuinely-missing map entry look the
  // same via `??` alone — both fall back to the raw id, which is at
  // least honest (visibly not a symbol) rather than a misleading label.
  const symbol = instrumentsQuery.isError
    ? plan.instrument_id
    : (instrumentsQuery.data?.get(plan.instrument_id)?.symbol ?? plan.instrument_id);
  const hasAssumptions = Object.keys(plan.assumptions).length > 0;

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <TradePlanResult plan={plan} symbol={symbol} linkToDetail={false} />

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            <span className="text-muted-foreground">Setup:</span> {plan.setup_type}
          </p>
          <p>
            <span className="text-muted-foreground">Plan date:</span> {plan.plan_date}
          </p>
          {plan.invalidation_conditions.length > 0 && (
            <div>
              <p className="text-muted-foreground">Invalidation conditions:</p>
              <ul className="list-inside list-disc">
                {plan.invalidation_conditions.map((condition) => (
                  <li key={condition}>{condition}</li>
                ))}
              </ul>
            </div>
          )}
          {hasAssumptions && (
            <div>
              <p className="text-muted-foreground">Assumptions:</p>
              <pre className="overflow-x-auto rounded bg-muted p-2 text-xs">
                {JSON.stringify(plan.assumptions, null, 2)}
              </pre>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            risk_version={plan.risk_version} score_version={plan.score_version ?? "—"}{" "}
            indicator_version={plan.indicator_version ?? "—"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
