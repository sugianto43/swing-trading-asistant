import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TradePlanResult } from "./trade-plan-result";
import type { TradePlan } from "@/lib/queries/risk";

function makeValidPlan(overrides: Partial<TradePlan> = {}): TradePlan {
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
    target_prices: [1100, 1150],
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

describe("TradePlanResult", () => {
  it("renders a VALID plan as a success card, never as an error", () => {
    render(<TradePlanResult plan={makeValidPlan()} symbol="BBCA" />);

    expect(screen.getByText("VALID")).toBeInTheDocument();
    expect(screen.getByText("BBCA: plan ready")).toBeInTheDocument();
    expect(screen.getByText("1050")).toBeInTheDocument();
    expect(screen.getByText("Targets: 1100, 1150")).toBeInTheDocument();
  });

  it("links the VALID result to the plan's own detail page", () => {
    render(<TradePlanResult plan={makeValidPlan({ id: "abc-123" })} symbol="BBCA" />);

    expect(screen.getByRole("link", { name: "BBCA: plan ready" })).toHaveAttribute(
      "href",
      "/risk/abc-123",
    );
  });

  it("links a VALID plan to the positions screen to record an execution against it", () => {
    render(<TradePlanResult plan={makeValidPlan({ id: "abc-123" })} symbol="BBCA" />);

    expect(screen.getByRole("link", { name: "Record execution →" })).toHaveAttribute(
      "href",
      "/positions?symbol=BBCA&trade_plan_id=abc-123",
    );
  });

  it("renders plain text, not a link, when linkToDetail is false", () => {
    render(<TradePlanResult plan={makeValidPlan({ id: "abc-123" })} symbol="BBCA" linkToDetail={false} />);

    expect(screen.getByText("BBCA: plan ready")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "BBCA: plan ready" })).not.toBeInTheDocument();
  });

  it("renders a REJECTED plan as its own distinct result, not an error state", () => {
    render(
      <TradePlanResult
        plan={makeValidPlan({ status: "REJECTED", rejection_reasons: ["no qualifying candidate"] })}
        symbol="BBCA"
      />,
    );

    expect(screen.getByText("REJECTED")).toBeInTheDocument();
    expect(screen.getByText("BBCA: plan rejected")).toBeInTheDocument();
    expect(screen.getByText("no qualifying candidate")).toBeInTheDocument();
  });

  it("renders every rejection reason the backend returned, not just the first", () => {
    render(
      <TradePlanResult
        plan={makeValidPlan({
          status: "REJECTED",
          rejection_reasons: ["reason one", "reason two"],
        })}
        symbol="BBCA"
      />,
    );

    expect(screen.getByText("reason one")).toBeInTheDocument();
    expect(screen.getByText("reason two")).toBeInTheDocument();
  });
});
