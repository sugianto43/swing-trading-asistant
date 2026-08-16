import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ExecutionResult } from "./execution-result";
import type { Position } from "@/lib/queries/positions";

function makePosition(overrides: Partial<Position> = {}): Position {
  return {
    id: "pos-1",
    instrument_id: "uuid-1",
    trade_plan_id: null,
    status: "OPEN",
    quantity_open: 100,
    avg_entry_price: 1050,
    avg_entry_fee_per_share: 5,
    cumulative_quantity_bought: 100,
    cumulative_entry_fees: 500,
    cumulative_exit_fees: 0,
    realized_pnl: 0,
    opened_at: "2024-03-01T02:30:00Z",
    closed_at: null,
    created_at: "2024-03-01T02:30:00Z",
    updated_at: "2024-03-01T02:30:00Z",
    ...overrides,
  };
}

describe("ExecutionResult", () => {
  it("renders the resulting position, linked to its own detail page", () => {
    render(<ExecutionResult position={makePosition()} symbol="BBCA" />);

    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "BBCA: execution recorded" })).toHaveAttribute(
      "href",
      "/positions/pos-1",
    );
    expect(screen.getByText("100")).toBeInTheDocument();
    expect(screen.getByText("1050")).toBeInTheDocument();
  });

  it("renders a closed position's status distinctly", () => {
    render(<ExecutionResult position={makePosition({ status: "CLOSED", quantity_open: 0 })} symbol="BBCA" />);

    expect(screen.getByText("CLOSED")).toBeInTheDocument();
  });
});
