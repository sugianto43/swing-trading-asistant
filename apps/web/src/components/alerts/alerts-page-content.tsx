"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { AlertsFiltersBar } from "@/components/alerts/alerts-filters";
import { AlertsList } from "@/components/alerts/alerts-list";
import { ConnectionIndicator } from "@/components/alerts/connection-indicator";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchAlerts, type AlertFilters } from "@/lib/queries/alerts";
import { fetchInstrumentsById } from "@/lib/queries/instruments";
import { useAlertsStream } from "@/lib/use-alerts-stream";

export function AlertsPageContent() {
  const [filters, setFilters] = useState<AlertFilters>({});
  const queryClient = useQueryClient();

  // The SSE push payload is a smaller shape than AlertOut (no `details`,
  // no `created_at` — confirmed by reading app/worker/alert_service.py's
  // _publish() directly). Rather than splice a hand-built partial record
  // into the list, a push just triggers a refetch of the real REST
  // endpoint — every rendered row's data is always genuinely sourced
  // from the backend's own deduplicated table, never fabricated
  // client-side.
  //
  // useAlertsStream's effect deps are [] by design (it never
  // re-subscribes), so onAlert must be a stable reference — an inline
  // arrow function here would only ever wire up the first render's
  // closure, silently discarding every later one. useCallback with
  // queryClient (a stable reference) as the only dependency honors that
  // contract explicitly rather than relying on this callback happening
  // not to close over anything reactive.
  const onAlert = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
  }, [queryClient]);
  const streamStatus = useAlertsStream(onAlert);

  const alertsQuery = useQuery({
    queryKey: ["alerts", filters],
    queryFn: () => fetchAlerts(filters),
  });
  const instrumentsQuery = useQuery({
    queryKey: ["instruments-by-id"],
    queryFn: fetchInstrumentsById,
  });

  let listSection: React.ReactNode;
  if (alertsQuery.isPending || instrumentsQuery.isPending) {
    listSection = (
      <div className="flex flex-col gap-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  } else if (alertsQuery.isError || instrumentsQuery.isError) {
    listSection = (
      <p className="p-6 text-center text-sm text-muted-foreground">
        Couldn&apos;t load alerts. Check that the API is reachable and retry.
      </p>
    );
  } else {
    listSection = (
      <AlertsList alerts={alertsQuery.data.items} instrumentsById={instrumentsQuery.data} />
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <AlertsFiltersBar filters={filters} onChange={setFilters} />
        <ConnectionIndicator status={streamStatus} />
      </div>
      {listSection}
    </div>
  );
}
