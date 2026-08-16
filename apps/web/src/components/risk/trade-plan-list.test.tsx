import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TradePlanList } from "./trade-plan-list";
import type { Instrument } from "@/lib/queries/instruments";
import type { TradePlan } from "@/lib/queries/risk";

function makePlan(overrides: Partial<TradePlan> = {}): TradePlan {
  return {
    id: "1",
    instrument_id: "uuid-1",
    scan_candidate_id: "candidate-1",
    setup_type: "BREAKOUT",
    plan_date: "2024-03-01",
    risk_version: "v1",
    score_version: "v1",
    indicator_version: "v1",
    status: "VALID",
    rejection_reasons: [],
    entry_price: 1050,
    stop_price: 1000,
    target_prices: [],
    quantity: 100,
    allocation_amount: 105_000,
    allocation_pct: 10.5,
    max_loss_amount: 5_000,
    risk_reward_ratio: 2.0,
    assumptions: {},
    invalidation_conditions: [],
    created_at: "2024-03-01T00:00:00Z",
    updated_at: "2024-03-01T00:00:00Z",
    ...overrides,
  };
}

const INSTRUMENT: Instrument = {
  id: "uuid-1",
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
};

describe("TradePlanList", () => {
  it("renders an explicit empty state rather than a blank table", () => {
    render(<TradePlanList plans={[]} instrumentsById={new Map()} />);
    expect(screen.getByText("No trade plans yet.")).toBeInTheDocument();
  });

  it("resolves the symbol via the instrument lookup, since TradePlanOut only carries instrument_id", () => {
    render(
      <TradePlanList
        plans={[makePlan()]}
        instrumentsById={new Map([["uuid-1", INSTRUMENT]])}
      />,
    );

    expect(screen.getByRole("link", { name: "BBCA" })).toHaveAttribute("href", "/risk/1");
  });

  it("renders an em dash rather than crashing when the instrument lookup is missing an entry", () => {
    render(<TradePlanList plans={[makePlan()]} instrumentsById={new Map()} />);

    expect(screen.getByRole("link", { name: "—" })).toBeInTheDocument();
  });

  it("shows plan status distinctly for VALID and REJECTED rows", () => {
    render(
      <TradePlanList
        plans={[
          makePlan({ id: "1", status: "VALID" }),
          makePlan({ id: "2", status: "REJECTED" }),
        ]}
        instrumentsById={new Map([["uuid-1", INSTRUMENT]])}
      />,
    );

    expect(screen.getByText("VALID")).toBeInTheDocument();
    expect(screen.getByText("REJECTED")).toBeInTheDocument();
  });
});
