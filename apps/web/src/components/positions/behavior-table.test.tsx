import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BehaviorTable } from "./behavior-table";

describe("BehaviorTable", () => {
  it("shows an empty state distinct from a table", () => {
    render(<BehaviorTable entries={[]} />);

    expect(screen.getByText("No closed positions yet.")).toBeInTheDocument();
  });

  it("links each row to its position detail page, not an instrument join", () => {
    render(
      <BehaviorTable
        entries={[
          { position_id: "pos-1", stop_violated: true, entry_deviation_pct: 2.5, quantity_deviation_pct: -1 },
        ]}
      />,
    );

    expect(screen.getByRole("link", { name: "pos-1" })).toHaveAttribute("href", "/positions/pos-1");
    expect(screen.getByText("Yes")).toBeInTheDocument();
    expect(screen.getByText("2.5%")).toBeInTheDocument();
  });

  it("renders null fields as a placeholder, not a crash", () => {
    render(
      <BehaviorTable
        entries={[
          { position_id: "pos-2", stop_violated: null, entry_deviation_pct: null, quantity_deviation_pct: null },
        ]}
      />,
    );

    expect(screen.getAllByText("—")).toHaveLength(3);
  });
});
