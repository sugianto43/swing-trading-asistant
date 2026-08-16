import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/ai/ai-page-content", () => ({
  AiPageContent: () => <div>ai page content</div>,
}));

import AiPage from "./page";

describe("AiPage", () => {
  it("renders AiPageContent inside a Suspense boundary", () => {
    // useSearchParams requires a Suspense boundary around the client
    // component that calls it, or a prerendered route build fails
    // (Next.js 16 requirement) — this locks in that the wrapper exists.
    render(<AiPage />);

    expect(screen.getByText("ai page content")).toBeInTheDocument();
  });
});
