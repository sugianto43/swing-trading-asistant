import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("renders the app shell heading", () => {
    render(<Home />);
    expect(screen.getByText("IDX Swing Trading Assistant")).toBeInTheDocument();
  });
});
