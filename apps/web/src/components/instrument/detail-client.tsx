"use client";

import { useQuery } from "@tanstack/react-query";

import { InstrumentHeader } from "@/components/instrument/header";
import { PriceChart } from "@/components/instrument/price-chart";
import { RecentCandidates } from "@/components/instrument/recent-candidates";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchRecentIndicators } from "@/lib/queries/indicators";
import { fetchInstrument, fetchRecentPriceBars } from "@/lib/queries/instruments";
import { fetchInstrumentCandidates } from "@/lib/queries/scanner";

export function InstrumentDetailClient({ symbol }: { symbol: string }) {
  const instrumentQuery = useQuery({
    queryKey: ["instrument", symbol],
    queryFn: () => fetchInstrument(symbol),
    retry: false,
  });
  const barsQuery = useQuery({
    queryKey: ["price-bars", symbol],
    queryFn: () => fetchRecentPriceBars(symbol),
    enabled: instrumentQuery.isSuccess,
  });
  const indicatorsQuery = useQuery({
    queryKey: ["indicators", symbol],
    queryFn: () => fetchRecentIndicators(symbol),
    enabled: instrumentQuery.isSuccess,
  });
  const candidatesQuery = useQuery({
    queryKey: ["instrument-candidates", symbol],
    queryFn: () => fetchInstrumentCandidates(symbol),
    enabled: instrumentQuery.isSuccess,
  });

  if (instrumentQuery.isPending) {
    return (
      <div className="flex flex-1 flex-col gap-3 p-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  const isNotFound = instrumentQuery.error?.message === "NOT_FOUND";

  if (isNotFound) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">No instrument found for &quot;{symbol}&quot;.</p>
      </div>
    );
  }

  if (instrumentQuery.isError || !instrumentQuery.data) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="font-medium">Couldn&apos;t load this instrument.</p>
        <p className="text-sm text-muted-foreground">Check that the API is reachable and retry.</p>
      </div>
    );
  }

  // Falling through to an empty chart/list on a fetch failure would look
  // identical to "this instrument genuinely has no price history/setups
  // yet" — distinct messaging here, rather than silently rendering an
  // empty state, matches how a genuine failure is never conflated with
  // confirmed-absent data elsewhere in this codebase.
  let priceSection: React.ReactNode;
  if (barsQuery.isError || indicatorsQuery.isError) {
    priceSection = (
      <p className="p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load price history.
      </p>
    );
  } else if (barsQuery.isPending || indicatorsQuery.isPending) {
    priceSection = <Skeleton className="h-96 w-full" />;
  } else {
    priceSection = <PriceChart bars={barsQuery.data ?? []} indicators={indicatorsQuery.data ?? []} />;
  }

  let candidatesSection: React.ReactNode;
  if (candidatesQuery.isError) {
    candidatesSection = (
      <p className="p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load recent setups.
      </p>
    );
  } else if (candidatesQuery.isPending) {
    candidatesSection = <Skeleton className="h-40 w-full" />;
  } else {
    candidatesSection = <RecentCandidates candidates={candidatesQuery.data ?? []} />;
  }

  return (
    <div className="flex flex-1 flex-col gap-3 p-4">
      <InstrumentHeader instrument={instrumentQuery.data} />
      {priceSection}
      {candidatesSection}
    </div>
  );
}
