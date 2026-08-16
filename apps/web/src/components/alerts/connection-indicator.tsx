import type { StreamStatus } from "@/lib/use-alerts-stream";

const LABEL: Record<StreamStatus, string> = {
  connecting: "Connecting…",
  open: "Live",
  error: "Reconnecting…",
};

// EventSource retries automatically on its own after an error (per the
// SSE spec) — "error" here means "temporarily disconnected, the browser
// is already retrying," not a fatal state, so it's labeled
// "Reconnecting…" rather than a hard failure.
const DOT_COLOR: Record<StreamStatus, string> = {
  connecting: "bg-muted-foreground",
  open: "bg-emerald-500",
  error: "bg-amber-500",
};

export function ConnectionIndicator({ status }: { status: StreamStatus }) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground" role="status">
      <span className={`inline-block size-2 rounded-full ${DOT_COLOR[status]}`} aria-hidden="true" />
      {LABEL[status]}
    </div>
  );
}
