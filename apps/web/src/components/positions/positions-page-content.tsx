"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { ExecutionForm } from "@/components/positions/execution-form";
import { PositionsFiltersBar } from "@/components/positions/positions-filters";
import { PositionsList } from "@/components/positions/positions-list";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchInstrumentsById } from "@/lib/queries/instruments";
import { fetchPositions, type PositionFilters } from "@/lib/queries/positions";

export function PositionsPageContent() {
  const searchParams = useSearchParams();
  const defaultSymbol = searchParams.get("symbol") ?? undefined;
  const defaultTradePlanId = searchParams.get("trade_plan_id") ?? undefined;
  const [filters, setFilters] = useState<PositionFilters>({});

  const positionsQuery = useQuery({
    queryKey: ["positions", filters],
    queryFn: () => fetchPositions(filters),
  });
  const instrumentsQuery = useQuery({
    queryKey: ["instruments-by-id"],
    queryFn: fetchInstrumentsById,
  });

  let listSection: React.ReactNode;
  if (positionsQuery.isPending || instrumentsQuery.isPending) {
    listSection = (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  } else if (positionsQuery.isError || instrumentsQuery.isError) {
    listSection = (
      <p className="p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load positions. Check that the API is reachable and retry.
      </p>
    );
  } else {
    listSection = (
      <PositionsList positions={positionsQuery.data.items} instrumentsById={instrumentsQuery.data} />
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <ExecutionForm defaultSymbol={defaultSymbol} defaultTradePlanId={defaultTradePlanId} />

      <div className="mt-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-muted-foreground">Open Positions</h2>
        <Link href="/positions/performance" className="text-sm text-primary hover:underline">
          View performance →
        </Link>
      </div>
      <PositionsFiltersBar filters={filters} onChange={setFilters} />
      {listSection}
    </div>
  );
}
