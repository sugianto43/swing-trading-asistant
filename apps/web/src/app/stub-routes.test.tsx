import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AiPage from "./ai/page";
import AlertsPage from "./alerts/page";

// Direct coverage of the actual route files, not just the shared
// StubPage component they wrap — a copy-paste mistake in one page's
// title or phase number wouldn't be caught by testing StubPage alone.
// overview/, scanner/, risk/, and positions/ are no longer stubs
// (Phase 13, 14, 15) — they have their own dedicated page tests now.
describe("stub routes", () => {
  it.each([
    ["/ai", AiPage, "AI Analyst", 16],
    ["/alerts", AlertsPage, "Alerts", 17],
  ] as const)("%s renders its title and phase", (_route, Page, title, phase) => {
    render(<Page />);
    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByText(`Coming in Phase ${phase}.`)).toBeInTheDocument();
  });
});
