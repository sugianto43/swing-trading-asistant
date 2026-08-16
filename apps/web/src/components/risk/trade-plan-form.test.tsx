import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const createTradePlan = vi.fn();
vi.mock("@/lib/queries/risk", () => ({
  createTradePlan: (payload: unknown) => createTradePlan(payload),
}));

import { TradePlanForm } from "./trade-plan-form";

function renderForm(props: React.ComponentProps<typeof TradePlanForm> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <TradePlanForm {...props} />
    </QueryClientProvider>,
  );
}

const VALID_PLAN = {
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
};

describe("TradePlanForm", () => {
  it("prefills symbol and plan date from props (URL search params, in real usage)", () => {
    renderForm({ defaultSymbol: "BBCA", defaultPlanDate: "2024-03-01" });

    expect(screen.getByLabelText("Symbol")).toHaveValue("BBCA");
    expect(screen.getByLabelText("Plan date")).toHaveValue("2024-03-01");
  });

  it("shows a validation error and never submits when capital is left blank", async () => {
    const user = userEvent.setup();
    renderForm({ defaultSymbol: "BBCA", defaultSetupType: "BREAKOUT" });

    await user.click(screen.getByRole("button", { name: "Build trade plan" }));

    await waitFor(() =>
      expect(screen.getByText("Capital must be a positive number")).toBeInTheDocument(),
    );
    expect(createTradePlan).not.toHaveBeenCalled();
  });

  it("renders the VALID result inline on successful submission", async () => {
    const user = userEvent.setup();
    createTradePlan.mockResolvedValueOnce(VALID_PLAN);
    renderForm({ defaultSymbol: "BBCA", defaultSetupType: "BREAKOUT" });

    await user.type(screen.getByLabelText("Capital (IDR)"), "100000000");
    await user.click(screen.getByRole("button", { name: "Build trade plan" }));

    await waitFor(() => expect(screen.getByText("BBCA: plan ready")).toBeInTheDocument());
  });

  it("renders the REJECTED result inline as a normal result, not an error", async () => {
    const user = userEvent.setup();
    createTradePlan.mockResolvedValueOnce({
      ...VALID_PLAN,
      status: "REJECTED",
      rejection_reasons: ["no qualifying candidate"],
    });
    renderForm({ defaultSymbol: "BBCA", defaultSetupType: "BREAKOUT" });

    await user.type(screen.getByLabelText("Capital (IDR)"), "100000000");
    await user.click(screen.getByRole("button", { name: "Build trade plan" }));

    await waitFor(() => expect(screen.getByText("BBCA: plan rejected")).toBeInTheDocument());
    expect(
      screen.queryByText("Couldn't build the trade plan. Check that the API is reachable and retry."),
    ).not.toBeInTheDocument();
  });

  it("shows a distinct error when the request itself fails", async () => {
    const user = userEvent.setup();
    createTradePlan.mockRejectedValueOnce(new Error("network down"));
    renderForm({ defaultSymbol: "BBCA", defaultSetupType: "BREAKOUT" });

    await user.type(screen.getByLabelText("Capital (IDR)"), "100000000");
    await user.click(screen.getByRole("button", { name: "Build trade plan" }));

    await waitFor(() =>
      expect(
        screen.getByText("Couldn't build the trade plan. Check that the API is reachable and retry."),
      ).toBeInTheDocument(),
    );
  });

  it("uppercases the symbol before submitting", async () => {
    const user = userEvent.setup();
    createTradePlan.mockResolvedValueOnce(VALID_PLAN);
    renderForm({ defaultSetupType: "BREAKOUT" });

    await user.type(screen.getByLabelText("Symbol"), "bbca");
    await user.type(screen.getByLabelText("Capital (IDR)"), "100000000");
    await user.click(screen.getByRole("button", { name: "Build trade plan" }));

    await waitFor(() =>
      expect(createTradePlan).toHaveBeenCalledWith(expect.objectContaining({ symbol: "BBCA" })),
    );
  });

  it("shows a validation error and never submits when symbol is blank", async () => {
    const user = userEvent.setup();
    renderForm({ defaultSetupType: "BREAKOUT" });

    await user.type(screen.getByLabelText("Capital (IDR)"), "100000000");
    await user.click(screen.getByRole("button", { name: "Build trade plan" }));

    await waitFor(() => expect(screen.getByText("Symbol is required")).toBeInTheDocument());
    expect(createTradePlan).not.toHaveBeenCalled();
  });

  it.each(["0", "-100"])(
    "rejects a non-positive capital value (%s), same as blank",
    async (value) => {
      const user = userEvent.setup();
      renderForm({ defaultSymbol: "BBCA", defaultSetupType: "BREAKOUT" });

      await user.type(screen.getByLabelText("Capital (IDR)"), value);
      await user.click(screen.getByRole("button", { name: "Build trade plan" }));

      await waitFor(() =>
        expect(screen.getByText("Capital must be a positive number")).toBeInTheDocument(),
      );
      expect(createTradePlan).not.toHaveBeenCalled();
    },
  );

  it("adds and removes existing-position rows", async () => {
    const user = userEvent.setup();
    renderForm({ defaultSymbol: "BBCA", defaultSetupType: "BREAKOUT" });

    expect(screen.queryByPlaceholderText("Symbol")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Add position" }));
    expect(screen.getByPlaceholderText("Symbol")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove" }));
    expect(screen.queryByPlaceholderText("Symbol")).not.toBeInTheDocument();
  });

  it("submits a filled existing-position row as part of the payload", async () => {
    const user = userEvent.setup();
    createTradePlan.mockResolvedValueOnce(VALID_PLAN);
    renderForm({ defaultSymbol: "BBCA", defaultSetupType: "BREAKOUT" });

    await user.click(screen.getByRole("button", { name: "Add position" }));
    await user.type(screen.getByPlaceholderText("Symbol"), "TLKM");
    await user.type(screen.getByPlaceholderText("Sector (optional)"), "Telco");
    await user.type(screen.getByPlaceholderText("Allocation amount"), "50000000");
    await user.type(screen.getByLabelText("Capital (IDR)"), "100000000");
    await user.click(screen.getByRole("button", { name: "Build trade plan" }));

    await waitFor(() =>
      expect(createTradePlan).toHaveBeenCalledWith(
        expect.objectContaining({
          existing_positions: [
            { symbol: "TLKM", sector: "Telco", allocation_amount: 50_000_000 },
          ],
        }),
      ),
    );
  });
});
