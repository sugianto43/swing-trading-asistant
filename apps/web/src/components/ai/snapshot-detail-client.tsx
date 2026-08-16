"use client";

import { useQuery } from "@tanstack/react-query";

import { AnalysisResult } from "@/components/ai/analysis-result";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchSnapshot } from "@/lib/queries/ai";

export function SnapshotDetailClient({ id }: { id: string }) {
  const snapshotQuery = useQuery({
    queryKey: ["ai-snapshot", id],
    queryFn: () => fetchSnapshot(id),
    retry: false,
  });

  if (snapshotQuery.isPending) {
    return (
      <div className="flex flex-1 flex-col gap-4 p-6">
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const isNotFound = snapshotQuery.error?.message === "NOT_FOUND";

  if (isNotFound) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">No analysis found for &quot;{id}&quot;.</p>
      </div>
    );
  }

  if (snapshotQuery.isError || !snapshotQuery.data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">Couldn&apos;t load this analysis.</p>
        <p className="text-sm text-muted-foreground">Check that the API is reachable and retry.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <AnalysisResult snapshot={snapshotQuery.data} />
    </div>
  );
}
