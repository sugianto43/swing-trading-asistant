import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const recordExecution = vi.fn();
vi.mock("@/lib/queries/positions", () => ({
  recordExecution: (payload: unknown) => recordExecution(payload),
}));

import { ExecutionForm } from "./execution-form";

function renderForm(props: React.ComponentProps<typeof ExecutionForm> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={queryClient}>
      <ExecutionForm {...props} />
    </QueryClientProvider>,
  );
  return { ...view, queryClient };
}

const POSITION = {
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

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Symbol"), "bbca");
  await user.click(screen.getByLabelText("Side"));
  await user.click(screen.getByRole("option", { name: "BUY" }));
  await user.type(screen.getByLabelText("Quantity"), "100");
  await user.type(screen.getByLabelText("Price (IDR)"), "1050");
  await user.type(screen.getByLabelText("Executed at"), "2024-03-01T09:30");
}

describe("ExecutionForm", () => {
  it("prefills symbol and trade plan id from props", () => {
    renderForm({ defaultSymbol: "BBCA", defaultTradePlanId: "plan-1" });

    expect(screen.getByLabelText("Symbol")).toHaveValue("BBCA");
  });

  it("shows a validation error and never submits when required fields are blank", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() => expect(screen.getByText("Symbol is required")).toBeInTheDocument());
    expect(recordExecution).not.toHaveBeenCalled();
  });

  it.each(["0", "-10"])("rejects a non-positive quantity (%s)", async (value) => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Symbol"), "BBCA");
    await user.click(screen.getByLabelText("Side"));
    await user.click(screen.getByRole("option", { name: "BUY" }));
    await user.type(screen.getByLabelText("Quantity"), value);
    await user.type(screen.getByLabelText("Price (IDR)"), "1050");
    await user.type(screen.getByLabelText("Executed at"), "2024-03-01T09:30");
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() =>
      expect(screen.getByText("Quantity must be a positive number")).toBeInTheDocument(),
    );
    expect(recordExecution).not.toHaveBeenCalled();
  });

  it("converts the local datetime-local value to a UTC ISO string before submitting", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    renderForm();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() => expect(recordExecution).toHaveBeenCalled());
    const payload = recordExecution.mock.calls[0][0];
    expect(payload.executed_at).toBe(new Date("2024-03-01T09:30").toISOString());
  });

  it("uppercases the symbol before submitting", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    renderForm();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() =>
      expect(recordExecution).toHaveBeenCalledWith(expect.objectContaining({ symbol: "BBCA" })),
    );
  });

  it("renders the resulting position on success", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    renderForm();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() =>
      expect(screen.getByText("BBCA: execution recorded")).toBeInTheDocument(),
    );
  });

  it("shows the backend's own message when the request fails (e.g. overselling), not a generic apology", async () => {
    const user = userEvent.setup();
    recordExecution.mockRejectedValueOnce(new Error("cannot sell 100 shares, only 50 open"));
    renderForm();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() =>
      expect(screen.getByText(/cannot sell 100 shares, only 50 open/)).toBeInTheDocument(),
    );
  });

  it("rejects a negative fee", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Symbol"), "BBCA");
    await user.click(screen.getByLabelText("Side"));
    await user.click(screen.getByRole("option", { name: "BUY" }));
    await user.type(screen.getByLabelText("Quantity"), "100");
    await user.type(screen.getByLabelText("Price (IDR)"), "1050");
    // fee defaults to 0 (already in the field) — userEvent.type appends
    // rather than replaces, and typing "-" after an existing digit is an
    // invalid intermediate value for a native number input (it clears
    // instead of composing "0-1"), so the field must be cleared first or
    // this never actually exercises a negative value.
    await user.clear(screen.getByLabelText("Fee (IDR)"));
    await user.type(screen.getByLabelText("Fee (IDR)"), "-1");
    await user.type(screen.getByLabelText("Executed at"), "2024-03-01T09:30");
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() => expect(screen.getByText("Fee cannot be negative")).toBeInTheDocument());
    expect(recordExecution).not.toHaveBeenCalled();
  });

  it("accepts a zero fee as the boundary-valid case", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    renderForm();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() =>
      expect(recordExecution).toHaveBeenCalledWith(expect.objectContaining({ fee: 0 })),
    );
  });

  it("forwards a prefilled trade_plan_id through to the request, with no visible field for the user to retype it", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    renderForm({ defaultTradePlanId: "plan-1" });

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() =>
      expect(recordExecution).toHaveBeenCalledWith(
        expect.objectContaining({ trade_plan_id: "plan-1" }),
      ),
    );
  });

  it("omits trade_plan_id entirely when not linked to a plan, rather than sending an empty string", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    renderForm();

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() => expect(recordExecution).toHaveBeenCalled());
    const payload = recordExecution.mock.calls[0][0];
    expect(payload.trade_plan_id).toBeUndefined();
  });

  it("invalidates this position's own detail/execution caches, not just the list, on success", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    const { queryClient } = renderForm();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    await fillRequiredFields(user);
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() => expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["positions"] }));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["position", POSITION.id] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["executions", POSITION.id] });
  });

  it("forwards optional notes when provided", async () => {
    const user = userEvent.setup();
    recordExecution.mockResolvedValueOnce(POSITION);
    renderForm();

    await fillRequiredFields(user);
    await user.type(screen.getByLabelText("Notes (optional)"), "filled at market open");
    await user.click(screen.getByRole("button", { name: "Record execution" }));

    await waitFor(() =>
      expect(recordExecution).toHaveBeenCalledWith(
        expect.objectContaining({ notes: "filled at market open" }),
      ),
    );
  });
});
