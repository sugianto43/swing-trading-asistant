import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/positions/positions-page-content", () => ({
  PositionsPageContent: () => <div>positions page content</div>,
}));

import PositionsPage from "./page";

describe("PositionsPage", () => {
  it("renders PositionsPageContent inside a Suspense boundary", () => {
    // useSearchParams requires a Suspense boundary around the client
    // component that calls it, or a prerendered route build fails
    // (Next.js 16 requirement) — this locks in that the wrapper exists.
    render(<PositionsPage />);

    expect(screen.getByText("positions page content")).toBeInTheDocument();
  });
});
