import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  // Test helpers, not part of the real EventSource API.
  emitOpen() {
    this.onopen?.();
  }
  emitMessage(data: string) {
    this.onmessage?.({ data } as MessageEvent<string>);
  }
  emitError() {
    this.onerror?.();
  }
}

vi.mock("@/lib/api/client", () => ({
  apiOrigin: () => "http://localhost:8000",
}));

import { useAlertsStream } from "./use-alerts-stream";

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal("EventSource", MockEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useAlertsStream", () => {
  it("connects to the absolute API origin's stream endpoint, not a relative (dev-server) URL", () => {
    renderHook(() => useAlertsStream(() => {}));

    expect(MockEventSource.instances[0].url).toBe("http://localhost:8000/api/v1/alerts/stream");
  });

  it("starts in the connecting status", () => {
    const { result } = renderHook(() => useAlertsStream(() => {}));

    expect(result.current).toBe("connecting");
  });

  it("moves to open status when the connection opens", async () => {
    const { result } = renderHook(() => useAlertsStream(() => {}));

    MockEventSource.instances[0].emitOpen();

    await waitFor(() => expect(result.current).toBe("open"));
  });

  it("moves to error status on a connection error", async () => {
    const { result } = renderHook(() => useAlertsStream(() => {}));

    MockEventSource.instances[0].emitError();

    await waitFor(() => expect(result.current).toBe("error"));
  });

  it("parses a real data message and forwards it to the callback", () => {
    const onAlert = vi.fn();
    renderHook(() => useAlertsStream(onAlert));

    const payload = {
      id: "1",
      alert_type: "BREAKOUT",
      instrument_id: "uuid-1",
      trigger_date: "2024-03-01",
      message: "BBCA broke out",
    };
    MockEventSource.instances[0].emitMessage(JSON.stringify(payload));

    expect(onAlert).toHaveBeenCalledWith(payload);
  });

  it("survives a malformed message without crashing or calling the callback with garbage", () => {
    const onAlert = vi.fn();
    renderHook(() => useAlertsStream(onAlert));

    // A real malformed payload should never happen (the backend always
    // publishes valid JSON), but the hook must not let a parse failure
    // take down the connection or the app — it should drop the one bad
    // message, not throw uncaught.
    expect(() => MockEventSource.instances[0].emitMessage("not json{")).not.toThrow();
    expect(onAlert).not.toHaveBeenCalled();
  });

  it("recovers to open status after an error, once the browser's automatic reconnect succeeds", async () => {
    const { result } = renderHook(() => useAlertsStream(() => {}));
    const instance = MockEventSource.instances[0];

    instance.emitError();
    await waitFor(() => expect(result.current).toBe("error"));

    // The browser's own reconnect logic reuses the same EventSource
    // instance and fires another 'open' event on success — it does not
    // create a new EventSource, so this simulates recovery on the same
    // mock instance rather than a fresh one.
    instance.emitOpen();
    await waitFor(() => expect(result.current).toBe("open"));
  });

  it("never calls the callback for a keep-alive (no onmessage event fires for comment-only SSE lines)", () => {
    // This documents the real SSE contract this hook relies on: a
    // `: keep-alive\n\n` line is a comment, and per spec never triggers
    // onmessage — there's nothing for the hook to filter. Simulated here
    // by simply never calling emitMessage and confirming the callback
    // stays untouched.
    const onAlert = vi.fn();
    renderHook(() => useAlertsStream(onAlert));

    expect(onAlert).not.toHaveBeenCalled();
  });

  it("closes the connection on unmount", () => {
    const { unmount } = renderHook(() => useAlertsStream(() => {}));
    const instance = MockEventSource.instances[0];

    unmount();

    expect(instance.closed).toBe(true);
  });
});
