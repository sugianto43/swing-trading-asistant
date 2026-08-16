import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/instrument/detail-client", () => ({
  InstrumentDetailClient: ({ symbol }: { symbol: string }) => <div>symbol={symbol}</div>,
}));

import InstrumentDetailPage from "./page";

describe("InstrumentDetailPage", () => {
  it("awaits the dynamic route param and passes it through to the client component", async () => {
    const element = await InstrumentDetailPage({
      params: Promise.resolve({ symbol: "BBCA" }),
      searchParams: Promise.resolve({}),
    });
    render(element);

    expect(screen.getByText("symbol=BBCA")).toBeInTheDocument();
  });
});
