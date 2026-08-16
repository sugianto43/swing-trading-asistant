import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StubPage } from "./stub-page";

describe("StubPage", () => {
  it("renders the title and the phase it's coming in", () => {
    render(<StubPage title="Market Overview" phase={13} />);

    expect(screen.getByRole("heading", { name: "Market Overview" })).toBeInTheDocument();
    expect(screen.getByText("Coming in Phase 13.")).toBeInTheDocument();
  });
});
