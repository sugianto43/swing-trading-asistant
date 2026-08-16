import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisSnapshot } from "@/lib/queries/ai";

function resultStatus(entry: { [key: string]: unknown }): string | undefined {
  const result = entry.result;
  if (result && typeof result === "object" && "status" in result && typeof result.status === "string") {
    return result.status;
  }
  return undefined;
}

function resultReason(entry: { [key: string]: unknown }): string | undefined {
  const result = entry.result;
  if (result && typeof result === "object" && "reason" in result && typeof result.reason === "string") {
    return result.reason;
  }
  return undefined;
}

// The orchestrator's tool-call results carry four statuses (app/ai/tools.py,
// app/ai/orchestrator.py): OK, DATA_UNAVAILABLE (nothing to report),
// REFUSED (the model requested a tool outside the allowlist — a
// guardrail-relevant event, not a routine miss), and ERROR (malformed
// tool arguments). All three non-OK statuses must look visibly different
// from a normal successful call, not just DATA_UNAVAILABLE.
const STATUS_BADGE_VARIANT: Record<string, "secondary" | "outline" | "destructive"> = {
  OK: "secondary",
  DATA_UNAVAILABLE: "outline",
  REFUSED: "destructive",
  ERROR: "destructive",
};

/** Renders one AnalysisSnapshot exactly as the backend returned it —
 * response text, guardrail flags, and per-tool-call status are never
 * conditionally hidden, summarized away, or auto-retried
 * (AI-GUARDRAILS.md: flags are for human review, not silent handling).
 *
 * Only `tool_calls` is rendered, not `structured_data_snapshot` too —
 * the orchestrator (app/ai/orchestrator.py) appends the exact same
 * {tool_name, arguments, result} entry to both lists for every call,
 * so they're duplicates of each other, not two different views. */
export function AnalysisResult({ snapshot }: { snapshot: AnalysisSnapshot }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{snapshot.question}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {snapshot.guardrail_flags.length > 0 && (
          <div className="flex flex-col gap-1.5 rounded-lg border border-destructive/30 bg-destructive/5 p-3">
            <p className="text-xs font-medium text-destructive">Guardrail flags</p>
            <div className="flex flex-wrap gap-1.5">
              {snapshot.guardrail_flags.map((flag) => (
                <Badge key={flag} variant="destructive">
                  {flag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        <p className="text-sm whitespace-pre-wrap">{snapshot.response}</p>

        {snapshot.tool_calls.length > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium text-muted-foreground">Tool calls</p>
            {snapshot.tool_calls.map((entry, index) => {
              const status = resultStatus(entry);
              const reason = resultReason(entry);
              const toolName = typeof entry.tool_name === "string" ? entry.tool_name : "unknown tool";
              return (
                <div
                  key={index}
                  className="flex flex-col gap-1 rounded-lg border border-border bg-muted p-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium">{toolName}</span>
                    <Badge variant={status ? STATUS_BADGE_VARIANT[status] ?? "outline" : "outline"}>
                      {status ?? "UNKNOWN"}
                    </Badge>
                    {reason && <span className="text-xs text-muted-foreground">{reason}</span>}
                  </div>
                  <pre className="overflow-x-auto text-xs text-muted-foreground">
                    {JSON.stringify(entry, null, 2)}
                  </pre>
                </div>
              );
            })}
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          provider={snapshot.provider} model={snapshot.model} prompt_version={snapshot.prompt_version}
        </p>
      </CardContent>
    </Card>
  );
}
