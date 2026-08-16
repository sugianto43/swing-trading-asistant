"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { CandidatesTable } from "@/components/scanner/candidates-table";
import { ScannerFiltersBar } from "@/components/scanner/filters";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchScanCandidates, type ScannerFilters } from "@/lib/queries/scanner";

export default function ScannerPage() {
  const [filters, setFilters] = useState<ScannerFilters>({});

  const { data, isPending, isError } = useQuery({
    queryKey: ["scanner-candidates", filters],
    queryFn: () => fetchScanCandidates(filters),
  });

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <ScannerFiltersBar filters={filters} onChange={setFilters} />

      {isPending && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {isError && (
        <p className="p-6 text-center text-sm text-muted-foreground">
          Couldn&apos;t load scan candidates. Check that the API is reachable and retry.
        </p>
      )}

      {data && <CandidatesTable candidates={data.items} />}
    </div>
  );
}
