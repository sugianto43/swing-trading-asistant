import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AlertsList } from "./alerts-list";
import type { Instrument } from "@/lib/queries/instruments";
import type { Alert } from "@/lib/queries/alerts";

const ALERT: Alert = {
  id: "1",
  alert_type: "BREAKOUT",
  instrument_id: "uuid-1",
  trigger_date: "2024-03-01",
  message: "BBCA broke out of its 20-day range",
  details: {},
  created_at: "2024-03-01T00:00:00Z",
};

const INSTRUMENT = { id: "uuid-1", symbol: "BBCA" } as Instrument;

describe("AlertsList", () => {
  it("shows an empty state distinct from a table", () => {
    render(<AlertsList alerts={[]} instrumentsById={new Map()} />);

    expect(screen.getByText("No alerts yet.")).toBeInTheDocument();
  });

  it("renders each alert with its joined symbol, type badge, and message", () => {
    render(<AlertsList alerts={[ALERT]} instrumentsById={new Map([["uuid-1", INSTRUMENT]])} />);

    expect(screen.getByText("BBCA")).toBeInTheDocument();
    expect(screen.getByText("BREAKOUT")).toBeInTheDocument();
    expect(screen.getByText("BBCA broke out of its 20-day range")).toBeInTheDocument();
    expect(screen.getByText("2024-03-01")).toBeInTheDocument();
  });

  it("falls back to a placeholder when the instrument lookup has no match", () => {
    render(<AlertsList alerts={[ALERT]} instrumentsById={new Map()} />);

    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
