import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/positions/position-detail-client", () => ({
  PositionDetailClient: ({ id }: { id: string }) => <div>id={id}</div>,
}));

import PositionDetailPage from "./page";

describe("PositionDetailPage", () => {
  it("awaits the dynamic route param and passes it through to the client component", async () => {
    const element = await PositionDetailPage({
      params: Promise.resolve({ id: "pos-1" }),
      searchParams: Promise.resolve({}),
    });
    render(element);

    expect(screen.getByText("id=pos-1")).toBeInTheDocument();
  });
});
