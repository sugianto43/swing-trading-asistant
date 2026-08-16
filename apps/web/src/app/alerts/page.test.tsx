import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/alerts/alerts-page-content", () => ({
  AlertsPageContent: () => <div>alerts page content</div>,
}));

import AlertsPage from "./page";

describe("AlertsPage", () => {
  it("renders AlertsPageContent", () => {
    render(<AlertsPage />);

    expect(screen.getByText("alerts page content")).toBeInTheDocument();
  });
});
