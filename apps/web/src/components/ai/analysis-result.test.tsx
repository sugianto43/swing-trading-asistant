import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnalysisResult } from "./analysis-result";
import type { AnalysisSnapshot } from "@/lib/queries/ai";

function makeSnapshot(overrides: Partial<AnalysisSnapshot> = {}): AnalysisSnapshot {
  return {
    id: "1",
    instrument_id: "uuid-1",
    provider: "gemini",
    model: "gemini-2.0-flash",
    prompt_version: "v1",
    question: "What is BBCA's current setup?",
    tool_calls: [],
    structured_data_snapshot: [],
    response: "BBCA is showing a breakout setup with strong relative volume.",
    guardrail_flags: [],
    created_at: "2024-03-01T00:00:00Z",
    ...overrides,
  };
}

describe("AnalysisResult", () => {
  it("renders the question and response", () => {
    render(<AnalysisResult snapshot={makeSnapshot()} />);

    expect(screen.getByText("What is BBCA's current setup?")).toBeInTheDocument();
    expect(
      screen.getByText("BBCA is showing a breakout setup with strong relative volume."),
    ).toBeInTheDocument();
  });

  it("never hides guardrail flags when present, even alongside an otherwise normal response", () => {
    render(
      <AnalysisResult
        snapshot={makeSnapshot({ guardrail_flags: ["certainty_claim", "order_placement_claim"] })}
      />,
    );

    expect(screen.getByText("Guardrail flags")).toBeInTheDocument();
    expect(screen.getByText("certainty_claim")).toBeInTheDocument();
    expect(screen.getByText("order_placement_claim")).toBeInTheDocument();
    // the flagged response itself must still be shown, never suppressed
    expect(
      screen.getByText("BBCA is showing a breakout setup with strong relative volume."),
    ).toBeInTheDocument();
  });

  it("omits the guardrail-flags banner when there are none, rather than always rendering an empty box", () => {
    render(<AnalysisResult snapshot={makeSnapshot({ guardrail_flags: [] })} />);

    expect(screen.queryByText("Guardrail flags")).not.toBeInTheDocument();
  });

  it("renders a DATA_UNAVAILABLE tool result distinctly from an OK one, with its reason visible", () => {
    render(
      <AnalysisResult
        snapshot={makeSnapshot({
          tool_calls: [
            {
              tool_name: "get_stock_snapshot",
              arguments: { symbol: "BBCA" },
              result: { status: "OK", close: 9500 },
            },
            {
              tool_name: "get_market_events",
              arguments: { symbol: "BBCA" },
              result: { status: "DATA_UNAVAILABLE", reason: "no events in range" },
            },
          ],
        })}
      />,
    );

    expect(screen.getByText("OK")).toBeInTheDocument();
    expect(screen.getByText("DATA_UNAVAILABLE")).toBeInTheDocument();
    expect(screen.getByText("no events in range")).toBeInTheDocument();
  });

  it("renders REFUSED distinctly from OK — a guardrail-relevant event (model requested a disallowed tool), not a routine miss", () => {
    render(
      <AnalysisResult
        snapshot={makeSnapshot({
          tool_calls: [
            {
              tool_name: "execute_trade",
              arguments: {},
              result: { status: "REFUSED", reason: "tool not permitted: 'execute_trade'" },
            },
          ],
        })}
      />,
    );

    const badge = screen.getByText("REFUSED");
    expect(badge.getAttribute("data-variant")).toBe("destructive");
    expect(screen.getByText("tool not permitted: 'execute_trade'")).toBeInTheDocument();
  });

  it("renders ERROR distinctly from OK — malformed tool-call arguments, not a successful call", () => {
    render(
      <AnalysisResult
        snapshot={makeSnapshot({
          tool_calls: [
            {
              tool_name: "get_stock_snapshot",
              arguments: {},
              result: { status: "ERROR", reason: "invalid arguments for 'get_stock_snapshot'" },
            },
          ],
        })}
      />,
    );

    expect(screen.getByText("ERROR").getAttribute("data-variant")).toBe("destructive");
  });

  it("does not double-render tool_calls and structured_data_snapshot, since the backend duplicates the same entries into both", () => {
    const entry = {
      tool_name: "get_stock_snapshot",
      arguments: { symbol: "BBCA" },
      result: { status: "OK", close: 9500 },
    };
    render(
      <AnalysisResult
        snapshot={makeSnapshot({ tool_calls: [entry], structured_data_snapshot: [entry] })}
      />,
    );

    expect(screen.getAllByText("get_stock_snapshot")).toHaveLength(1);
  });

  it("omits the tool-calls section when there were none", () => {
    render(<AnalysisResult snapshot={makeSnapshot({ tool_calls: [] })} />);

    expect(screen.queryByText("Tool calls")).not.toBeInTheDocument();
  });

  it("renders lineage (provider/model/prompt_version)", () => {
    render(<AnalysisResult snapshot={makeSnapshot()} />);

    expect(
      screen.getByText("provider=gemini model=gemini-2.0-flash prompt_version=v1"),
    ).toBeInTheDocument();
  });
});
