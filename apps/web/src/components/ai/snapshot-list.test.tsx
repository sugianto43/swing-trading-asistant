import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SnapshotList } from "./snapshot-list";
import type { Instrument } from "@/lib/queries/instruments";
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
    response: "answer",
    guardrail_flags: [],
    created_at: "2024-03-01T00:00:00Z",
    ...overrides,
  };
}

const INSTRUMENT = { id: "uuid-1", symbol: "BBCA" } as Instrument;

describe("SnapshotList", () => {
  it("shows an empty state distinct from a table", () => {
    render(<SnapshotList snapshots={[]} instrumentsById={new Map()} />);

    expect(screen.getByText("No analyses yet.")).toBeInTheDocument();
  });

  it("renders each snapshot with its joined symbol, linked to the detail page", () => {
    render(
      <SnapshotList snapshots={[makeSnapshot()]} instrumentsById={new Map([["uuid-1", INSTRUMENT]])} />,
    );

    expect(screen.getByRole("link", { name: "BBCA" })).toHaveAttribute("href", "/ai/1");
  });

  it("falls back to a placeholder when instrument_id is null (no symbol scope on the question)", () => {
    render(
      <SnapshotList
        snapshots={[makeSnapshot({ instrument_id: null })]}
        instrumentsById={new Map([["uuid-1", INSTRUMENT]])}
      />,
    );

    expect(screen.getByRole("link", { name: "—" })).toBeInTheDocument();
  });

  it("truncates a long question in the preview", () => {
    const longQuestion = "a".repeat(200);
    render(
      <SnapshotList
        snapshots={[makeSnapshot({ question: longQuestion })]}
        instrumentsById={new Map()}
      />,
    );

    expect(screen.queryByText(longQuestion)).not.toBeInTheDocument();
    expect(screen.getByText(`${"a".repeat(80)}…`)).toBeInTheDocument();
  });

  it("shows a flagged badge only when guardrail_flags is non-empty", () => {
    const { rerender } = render(
      <SnapshotList
        snapshots={[makeSnapshot({ guardrail_flags: ["certainty_claim"] })]}
        instrumentsById={new Map()}
      />,
    );
    expect(screen.getByText("1 flagged")).toBeInTheDocument();

    rerender(
      <SnapshotList snapshots={[makeSnapshot({ guardrail_flags: [] })]} instrumentsById={new Map()} />,
    );
    expect(screen.queryByText(/flagged/)).not.toBeInTheDocument();
  });
});
