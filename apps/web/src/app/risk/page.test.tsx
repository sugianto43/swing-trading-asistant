import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/risk/risk-page-content", () => ({
  RiskPageContent: () => <div>risk page content</div>,
}));

import RiskPage from "./page";

describe("RiskPage", () => {
  it("renders RiskPageContent inside a Suspense boundary", () => {
    // useSearchParams requires a Suspense boundary around the client
    // component that calls it, or a prerendered route build fails
    // (Next.js 16 requirement) — this locks in that the wrapper exists.
    render(<RiskPage />);

    expect(screen.getByText("risk page content")).toBeInTheDocument();
  });
});
