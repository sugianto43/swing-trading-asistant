"use client";

import { useQuery } from "@tanstack/react-query";

import { BreadthStats } from "@/components/overview/breadth-stats";
import { SectorPerformanceList } from "@/components/overview/sector-performance-list";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchLatestBreadth } from "@/lib/queries/breadth";
import { fetchSectorPerformance } from "@/lib/queries/sector-performance";

export default function OverviewPage() {
  const breadthQuery = useQuery({
    queryKey: ["breadth", "latest"],
    queryFn: fetchLatestBreadth,
    retry: false,
  });

  // Sector performance needs an as_of date the backend actually has data
  // for — chaining off the latest breadth's own as_of (rather than
  // "today") means this resolves to real data on the first paint in the
  // common case, instead of an empty result for a date nothing's been
  // computed for yet.
  const sectorQuery = useQuery({
    queryKey: ["sector-performance", breadthQuery.data?.as_of],
    queryFn: () => fetchSectorPerformance(breadthQuery.data!.as_of),
    enabled: !!breadthQuery.data,
  });

  if (breadthQuery.isPending) {
    return (
      <div className="flex flex-1 flex-col gap-3 p-4">
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const isNotFound = breadthQuery.error?.message === "NOT_FOUND";

  if (breadthQuery.isError && !isNotFound) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">Couldn&apos;t load market breadth.</p>
        <p className="text-sm text-muted-foreground">Check that the API is reachable and retry.</p>
      </div>
    );
  }

  if (isNotFound || !breadthQuery.data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">No market breadth computed yet.</p>
        <p className="text-sm text-muted-foreground">
          Run the breadth computation (worker/CLI) to see the overview here.
        </p>
      </div>
    );
  }

  let sectorSection: React.ReactNode;
  if (sectorQuery.data) {
    sectorSection = <SectorPerformanceList sectors={sectorQuery.data} />;
  } else if (sectorQuery.isPending) {
    sectorSection = <Skeleton className="h-64 w-full" />;
  } else if (sectorQuery.isError) {
    // Distinct from "the backend confirmed zero sectors qualify" —
    // falling through to an empty list here would silently mask a real
    // fetch failure as a confirmed-empty result.
    sectorSection = (
      <p className="p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load sector performance.
      </p>
    );
  } else {
    sectorSection = <SectorPerformanceList sectors={[]} />;
  }

  return (
    <div className="flex flex-1 flex-col gap-3 p-4">
      <BreadthStats breadth={breadthQuery.data} />
      {sectorSection}
    </div>
  );
}
