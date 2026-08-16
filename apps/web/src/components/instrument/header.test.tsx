import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { InstrumentHeader } from "./header";
import type { Instrument } from "@/lib/queries/instruments";

function makeInstrument(overrides: Partial<Instrument> = {}): Instrument {
  return {
    id: "1",
    symbol: "BBCA",
    company_name: "Bank Central Asia Tbk",
    exchange: "IDX",
    currency: "IDR",
    security_type: "EQUITY",
    sector: "Banking",
    subsector: null,
    listing_date: null,
    delisting_date: null,
    status: "ACTIVE",
    source: "fixture",
    source_symbol: "BBCA.JK",
    ...overrides,
  };
}

describe("InstrumentHeader", () => {
  it("renders symbol, company name, sector, and status", () => {
    render(<InstrumentHeader instrument={makeInstrument()} />);

    expect(screen.getByText("BBCA")).toBeInTheDocument();
    expect(screen.getByText("Bank Central Asia Tbk")).toBeInTheDocument();
    expect(screen.getByText("Banking")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  });

  it("omits the sector badge when the instrument has none, rather than showing an empty badge", () => {
    render(<InstrumentHeader instrument={makeInstrument({ sector: null })} />);
    expect(screen.queryByText("Banking")).not.toBeInTheDocument();
  });

  it("renders SUSPENDED and DELISTED with different badge styling, not the same 'not ACTIVE' treatment", () => {
    const { unmount } = render(<InstrumentHeader instrument={makeInstrument({ status: "SUSPENDED" })} />);
    const suspendedVariant = screen.getByText("SUSPENDED").getAttribute("data-variant");
    unmount();

    render(<InstrumentHeader instrument={makeInstrument({ status: "DELISTED" })} />);
    const delistedVariant = screen.getByText("DELISTED").getAttribute("data-variant");

    expect(suspendedVariant).not.toBe(delistedVariant);
    expect(delistedVariant).toBe("destructive");
  });
});
