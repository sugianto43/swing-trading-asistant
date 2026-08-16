import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { ThemeProvider } from "next-themes";
import { describe, expect, it, vi } from "vitest";

import { makeQueryClient } from "@/lib/query-client";

vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: vi.fn(async () => ({ data: {}, error: undefined })) },
}));

import { Nav } from "./nav";

function renderNav() {
  const queryClient = makeQueryClient();
  return render(
    <ThemeProvider attribute="class">
      <QueryClientProvider client={queryClient}>
        <Nav />
      </QueryClientProvider>
    </ThemeProvider>,
  );
}

describe("Nav", () => {
  it("renders a link for every dashboard section", () => {
    renderNav();

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
    renderNav();
    expect(screen.getByRole("link", { name: "IDX Swing Trading Assistant" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
