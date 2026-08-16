import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ScannerFiltersBar } from "./filters";

describe("ScannerFiltersBar", () => {
  it("updates the sector filter as free text and resets to page 1", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ScannerFiltersBar filters={{ page: 3 }} onChange={onChange} />);

    await user.type(screen.getByLabelText("Sector"), "B");

    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ sector: "B", page: 1 }),
    );
  });

  it("parses the min-score input as a number", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ScannerFiltersBar filters={{}} onChange={onChange} />);

    await user.type(screen.getByLabelText("Minimum score"), "7");

    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ minScore: 7, page: 1 }));
  });

  it("resets min-score to undefined when the input is cleared, not NaN or 0", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ScannerFiltersBar filters={{ minScore: 70 }} onChange={onChange} />);

    await user.clear(screen.getByLabelText("Minimum score"));

    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ minScore: undefined, page: 1 }),
    );
  });
});
