import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PositionsList } from "./positions-list";
import type { Instrument } from "@/lib/queries/instruments";
import type { Position } from "@/lib/queries/positions";

const POSITION: Position = {
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
};

const INSTRUMENT = { id: "uuid-1", symbol: "BBCA" } as Instrument;

describe("PositionsList", () => {
  it("shows an empty state distinct from a table", () => {
    render(<PositionsList positions={[]} instrumentsById={new Map()} />);

    expect(screen.getByText("No positions yet.")).toBeInTheDocument();
  });

  it("renders each position with its joined symbol and status badge", () => {
    render(
      <PositionsList positions={[POSITION]} instrumentsById={new Map([["uuid-1", INSTRUMENT]])} />,
    );

    expect(screen.getByRole("link", { name: "BBCA" })).toHaveAttribute("href", "/positions/pos-1");
    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("falls back to a placeholder when the instrument lookup has no match", () => {
    render(<PositionsList positions={[POSITION]} instrumentsById={new Map()} />);

    expect(screen.getByRole("link", { name: "—" })).toBeInTheDocument();
  });
});
