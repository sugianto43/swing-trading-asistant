import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { ThemeProvider } from "next-themes";
import { describe, expect, it, vi } from "vitest";

import { makeQueryClient } from "@/lib/query-client";

vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: vi.fn(async () => ({ data: {}, error: undefined })) },
}));

let mockPathname = "/overview";
vi.mock("next/navigation", () => ({
  usePathname: () => mockPathname,
}));

import { Sidebar } from "./sidebar";

function renderSidebar() {
  const queryClient = makeQueryClient();
  return render(
    <ThemeProvider attribute="class">
      <QueryClientProvider client={queryClient}>
        <Sidebar />
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("Sidebar", () => {
  it("renders a link for every dashboard section", () => {
    renderSidebar();

    const expected: [string, string][] = [
      ["Overview", "/overview"],
      ["Scanner", "/scanner"],
      ["Risk", "/risk"],
      ["Positions", "/positions"],
      ["AI", "/ai"],
      ["Alerts", "/alerts"],
    ];

    for (const [label, href] of expected) {
      expect(screen.getByRole("link", { name: label })).toHaveAttribute("href", href);
    }
  });

  it("renders the brand link back to the home page", () => {
    renderSidebar();
    expect(screen.getByRole("link", { name: "IDX Swing Trading Assistant" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("highlights the active route's link distinctly from the others", () => {
    mockPathname = "/scanner";
    renderSidebar();

    const scannerClass = screen.getByRole("link", { name: "Scanner" }).className;
    const overviewClass = screen.getByRole("link", { name: "Overview" }).className;
    expect(scannerClass).not.toBe(overviewClass);
  });

  it("also highlights nested detail routes under their parent section", () => {
    mockPathname = "/positions/abc-123";
    renderSidebar();

    const positionsClass = screen.getByRole("link", { name: "Positions" }).className;
    const scannerClass = screen.getByRole("link", { name: "Scanner" }).className;
    expect(positionsClass).not.toBe(scannerClass);
  });
});
