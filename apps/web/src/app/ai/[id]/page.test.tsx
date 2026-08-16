import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/ai/snapshot-detail-client", () => ({
  SnapshotDetailClient: ({ id }: { id: string }) => <div>id={id}</div>,
}));

import SnapshotDetailPage from "./page";

describe("SnapshotDetailPage", () => {
  it("awaits the dynamic route param and passes it through to the client component", async () => {
    const element = await SnapshotDetailPage({
      params: Promise.resolve({ id: "abc-123" }),
      searchParams: Promise.resolve({}),
    });
    render(element);

    expect(screen.getByText("id=abc-123")).toBeInTheDocument();
  });
});
