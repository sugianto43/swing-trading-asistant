"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";

import { AnalyzeForm } from "@/components/ai/analyze-form";
import { SnapshotList } from "@/components/ai/snapshot-list";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchInstrumentsById } from "@/lib/queries/instruments";
import { fetchSnapshots } from "@/lib/queries/ai";

export function AiPageContent() {
  const searchParams = useSearchParams();
  const defaultSymbol = searchParams.get("symbol") ?? undefined;

  const snapshotsQuery = useQuery({
    queryKey: ["ai-snapshots"],
    queryFn: () => fetchSnapshots({}),
  });
  const instrumentsQuery = useQuery({
    queryKey: ["instruments-by-id"],
    queryFn: fetchInstrumentsById,
  });

  let listSection: React.ReactNode;
  if (snapshotsQuery.isPending || instrumentsQuery.isPending) {
    listSection = (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  } else if (snapshotsQuery.isError || instrumentsQuery.isError) {
    listSection = (
      <p className="p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load past analyses. Check that the API is reachable and retry.
      </p>
    );
  } else {
    listSection = (
      <SnapshotList snapshots={snapshotsQuery.data.items} instrumentsById={instrumentsQuery.data} />
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-3 p-4">
      <AnalyzeForm defaultSymbol={defaultSymbol} />

      <h2 className="mt-4 text-sm font-medium text-muted-foreground">Recent Analyses</h2>
      {listSection}
    </div>
  );
}
