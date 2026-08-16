"use client";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";

async function fetchHealth(): Promise<boolean> {
  const { error } = await apiClient.GET("/api/v1/health");
  if (error) throw new Error("health check failed");
  return true;
}

export function ApiStatus() {
  const { isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  // fetchHealth only ever resolves to `true` or throws (surfacing as
  // isError) — there's no third "resolved but falsy" state to guard
  // against, so isPending/isError are the only two branches that matter.
  const label = isPending ? "Checking API…" : isError ? "API: disconnected" : "API: connected";
  const dotColor = isPending ? "bg-muted-foreground" : isError ? "bg-destructive" : "bg-emerald-500";

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground" role="status">
      <span className={`inline-block size-2 rounded-full ${dotColor}`} aria-hidden="true" />
      {label}
    </div>
  );
}
