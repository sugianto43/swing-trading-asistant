"use client";

import { useQuery } from "@tanstack/react-query";

import { BehaviorTable } from "@/components/positions/behavior-table";
import { PerformanceGroupTable } from "@/components/positions/performance-group-table";
import { PerformanceSummary } from "@/components/positions/performance-summary";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchPerformanceBehavior,
  fetchPerformanceByHoldingPeriod,
  fetchPerformanceByScoreBucket,
  fetchPerformanceBySector,
  fetchPerformanceBySetup,
  fetchPerformanceSummary,
} from "@/lib/queries/performance";

export function PerformancePageContent() {
  const summaryQuery = useQuery({ queryKey: ["performance-summary"], queryFn: fetchPerformanceSummary });
  const bySetupQuery = useQuery({ queryKey: ["performance-by-setup"], queryFn: fetchPerformanceBySetup });
  const bySectorQuery = useQuery({
    queryKey: ["performance-by-sector"],
    queryFn: fetchPerformanceBySector,
  });
  const byHoldingPeriodQuery = useQuery({
    queryKey: ["performance-by-holding-period"],
    queryFn: fetchPerformanceByHoldingPeriod,
  });
  const byScoreBucketQuery = useQuery({
    queryKey: ["performance-by-score-bucket"],
    queryFn: fetchPerformanceByScoreBucket,
  });
  const behaviorQuery = useQuery({ queryKey: ["performance-behavior"], queryFn: fetchPerformanceBehavior });

  const queries = [
    summaryQuery,
    bySetupQuery,
    bySectorQuery,
    byHoldingPeriodQuery,
    byScoreBucketQuery,
    behaviorQuery,
  ];
  const isPending = queries.some((q) => q.isPending);
  const isError = queries.some((q) => q.isError);

  if (isPending) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-6">
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !summaryQuery.data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">Couldn&apos;t load performance data.</p>
        <p className="text-sm text-muted-foreground">Check that the API is reachable and retry.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PerformanceSummary summary={summaryQuery.data} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <PerformanceGroupTable title="By Setup" groups={bySetupQuery.data ?? []} keyLabel="Setup" />
        <PerformanceGroupTable title="By Sector" groups={bySectorQuery.data ?? []} keyLabel="Sector" />
        <PerformanceGroupTable
          title="By Holding Period"
          groups={byHoldingPeriodQuery.data ?? []}
          keyLabel="Holding Period"
        />
        <PerformanceGroupTable
          title="By Score Bucket"
          groups={byScoreBucketQuery.data ?? []}
          keyLabel="Score Bucket"
        />
      </div>

      <div>
        <h3 className="mb-2 text-sm font-medium text-muted-foreground">Behavior</h3>
        <BehaviorTable entries={behaviorQuery.data ?? []} />
      </div>
    </div>
  );
}
