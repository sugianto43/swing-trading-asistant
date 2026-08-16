import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/risk/trade-plan-detail-client", () => ({
  TradePlanDetailClient: ({ id }: { id: string }) => <div>id={id}</div>,
}));

import TradePlanDetailPage from "./page";

describe("TradePlanDetailPage", () => {
  it("awaits the dynamic route param and passes it through to the client component", async () => {
    const element = await TradePlanDetailPage({
      params: Promise.resolve({ id: "abc-123" }),
      searchParams: Promise.resolve({}),
    });
    render(element);

    expect(screen.getByText("id=abc-123")).toBeInTheDocument();
  });
});
