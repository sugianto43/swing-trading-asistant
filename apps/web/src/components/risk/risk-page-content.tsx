"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";

import { TradePlanForm } from "@/components/risk/trade-plan-form";
import { TradePlanList } from "@/components/risk/trade-plan-list";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchInstrumentsById } from "@/lib/queries/instruments";
import { fetchTradePlans } from "@/lib/queries/risk";
import type { SetupType } from "@/lib/queries/setup-types";

export function RiskPageContent() {
  const searchParams = useSearchParams();
  const defaultSymbol = searchParams.get("symbol") ?? undefined;
  const defaultSetupType = (searchParams.get("setup") as SetupType | null) ?? undefined;
  const defaultPlanDate = searchParams.get("date") ?? undefined;

  const plansQuery = useQuery({
    queryKey: ["trade-plans"],
    queryFn: () => fetchTradePlans({}),
  });
  const instrumentsQuery = useQuery({
    queryKey: ["instruments-by-id"],
    queryFn: fetchInstrumentsById,
  });

  let plansSection: React.ReactNode;
  if (plansQuery.isPending || instrumentsQuery.isPending) {
    plansSection = (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  } else if (plansQuery.isError || instrumentsQuery.isError) {
    plansSection = (
      <p className="p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load trade plans. Check that the API is reachable and retry.
      </p>
    );
  } else {
    plansSection = (
      <TradePlanList plans={plansQuery.data.items} instrumentsById={instrumentsQuery.data} />
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <TradePlanForm
        defaultSymbol={defaultSymbol}
        defaultSetupType={defaultSetupType}
        defaultPlanDate={defaultPlanDate}
      />

      <h2 className="mt-4 text-sm font-medium text-muted-foreground">Existing Trade Plans</h2>
      {plansSection}
    </div>
  );
}
