import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ConnectionIndicator } from "./connection-indicator";

describe("ConnectionIndicator", () => {
  it("labels the connecting state", () => {
    render(<ConnectionIndicator status="connecting" />);
    expect(screen.getByText("Connecting…")).toBeInTheDocument();
  });

  it("labels the open state as Live", () => {
    render(<ConnectionIndicator status="open" />);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("labels the error state as Reconnecting, not a hard failure — EventSource retries on its own", () => {
    render(<ConnectionIndicator status="error" />);
    expect(screen.getByText("Reconnecting…")).toBeInTheDocument();
  });
});
