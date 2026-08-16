import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AiPage from "./ai/page";
import AlertsPage from "./alerts/page";
import PositionsPage from "./positions/page";
import RiskPage from "./risk/page";

// Direct coverage of the actual route files, not just the shared
// StubPage component they wrap — a copy-paste mistake in one page's
// title or phase number wouldn't be caught by testing StubPage alone.
// overview/ and scanner/ are no longer stubs as of Phase 13 — they have
// their own dedicated page tests now.
describe("stub routes", () => {
  it.each([
    ["/risk", RiskPage, "Risk & Trade Plan", 14],
    ["/positions", PositionsPage, "Positions, Journal & Performance", 15],
    ["/ai", AiPage, "AI Analyst", 16],
    ["/alerts", AlertsPage, "Alerts", 17],
  ] as const)("%s renders its title and phase", (_route, Page, title, phase) => {
    render(<Page />);
    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByText(`Coming in Phase ${phase}.`)).toBeInTheDocument();
  });
});
