import { useEffect, useState } from "react";

import { apiOrigin } from "@/lib/api/client";

export type StreamStatus = "connecting" | "open" | "error";

export interface AlertEvent {
  id: string;
  alert_type: string;
  instrument_id: string;
  trigger_date: string;
  message: string;
}

/** Subscribes to Phase 10's SSE endpoint. `EventSource` itself is the
 * browser's own long-lived connection with built-in automatic
 * reconnect-on-drop (per the SSE spec) — this hook only surfaces
 * connection status, it never manually recreates the connection except
 * on unmount/url change. `: keep-alive\n\n` comment-only lines the
 * backend sends every SSE_STREAM_TIMEOUT_SECONDS never reach onmessage
 * at all (that's native SSE behavior, not something to filter here) —
 * they exist purely to hold the connection open through idle proxies. */
export function useAlertsStream(onAlert: (event: AlertEvent) => void): StreamStatus {
  const [status, setStatus] = useState<StreamStatus>("connecting");

  useEffect(() => {
    const url = `${apiOrigin()}/api/v1/alerts/stream`;
    const source = new EventSource(url);

    source.onopen = () => setStatus("open");
    source.onerror = () => setStatus("error");
    source.onmessage = (event: MessageEvent<string>) => {
      // The backend always publishes valid JSON, but a parse failure
      // here must never throw uncaught out of a DOM event handler —
      // that would surface as an unhandled exception with no error
      // boundary to catch it. Drop the one bad message and keep the
      // connection alive rather than let it take anything down.
      try {
        onAlert(JSON.parse(event.data) as AlertEvent);
      } catch {
        // malformed message dropped, connection stays open
      }
    };

    return () => {
      source.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onAlert is expected to be stable per caller (mirrors other event-subscription hooks in this codebase); re-subscribing on every render would thrash the connection.
  }, []);

  return status;
}
