import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AlertsFiltersBar } from "./alerts-filters";

describe("AlertsFiltersBar", () => {
  it("forwards a selected alert type and resets to page 1", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AlertsFiltersBar filters={{ page: 3 }} onChange={onChange} />);

    await user.click(screen.getByLabelText("Alert type"));
    await user.click(screen.getByRole("option", { name: "BREAKOUT" }));

    expect(onChange).toHaveBeenCalledWith({ page: 1, alertType: "BREAKOUT" });
  });

  it("clears the alert type back to undefined when 'All alert types' is chosen", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AlertsFiltersBar filters={{ alertType: "BREAKOUT" }} onChange={onChange} />);

    await user.click(screen.getByLabelText("Alert type"));
    await user.click(screen.getByRole("option", { name: "All alert types" }));

    expect(onChange).toHaveBeenCalledWith({ alertType: undefined, page: 1 });
  });

  it("forwards a typed symbol and resets to page 1", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AlertsFiltersBar filters={{ page: 3 }} onChange={onChange} />);

    await user.type(screen.getByLabelText("Symbol filter"), "B");

    expect(onChange).toHaveBeenCalledWith({ page: 1, symbol: "B" });
  });

  it("forwards a chosen trigger date and resets to page 1", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<AlertsFiltersBar filters={{ page: 3 }} onChange={onChange} />);

    await user.type(screen.getByLabelText("Trigger date"), "2024-03-01");

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
    const lastCall = onChange.mock.calls.at(-1)?.[0];
    expect(lastCall.triggerDate).toBe("2024-03-01");
  });
});
