import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/positions/performance-page-content", () => ({
  PerformancePageContent: () => <div>performance page content</div>,
}));

import PerformancePage from "./page";

describe("PerformancePage", () => {
  it("renders PerformancePageContent", () => {
    render(<PerformancePage />);

    expect(screen.getByText("performance page content")).toBeInTheDocument();
  });
});
