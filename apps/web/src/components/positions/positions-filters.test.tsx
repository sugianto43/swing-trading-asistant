import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PositionsFiltersBar } from "./positions-filters";

describe("PositionsFiltersBar", () => {
  it("forwards a typed symbol and resets to page 1", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PositionsFiltersBar filters={{ page: 3 }} onChange={onChange} />);

    await user.type(screen.getByLabelText("Symbol filter"), "B");

    expect(onChange).toHaveBeenCalledWith({ page: 1, symbol: "B" });
  });

  it("forwards a selected status and resets to page 1", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PositionsFiltersBar filters={{ page: 3 }} onChange={onChange} />);

    await user.click(screen.getByLabelText("Status"));
    await user.click(screen.getByRole("option", { name: "OPEN" }));

    expect(onChange).toHaveBeenCalledWith({ page: 1, status: "OPEN" });
  });

  it("clears the status filter back to undefined when 'All statuses' is chosen", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PositionsFiltersBar filters={{ status: "OPEN" }} onChange={onChange} />);

    await user.click(screen.getByLabelText("Status"));
    await user.click(screen.getByRole("option", { name: "All statuses" }));

    expect(onChange).toHaveBeenCalledWith({ status: undefined, page: 1 });
  });
});
