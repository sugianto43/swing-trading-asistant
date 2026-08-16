import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
const postMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: (...args: unknown[]) => postMock(...args),
  },
}));

import { analyzeQuestion, fetchSnapshot, fetchSnapshots } from "./ai";

describe("analyzeQuestion", () => {
  it("returns the persisted snapshot on success", async () => {
    const snapshot = { id: "1", response: "BBCA looks like a breakout setup.", guardrail_flags: [] };
    postMock.mockResolvedValueOnce({ data: snapshot, error: undefined });

    await expect(analyzeQuestion({ question: "What is BBCA's setup?" })).resolves.toEqual(snapshot);
  });

  it("throws the backend's own error message on a genuine failure (e.g. no provider configured)", async () => {
    // Real runtime shape (app/errors.py's global exception handler wraps
    // every error in {"error": {"code", "message", "details"}}) — not
    // FastAPI's bare default {"detail": "..."}, which openapi-fetch's
    // generated types don't reflect. A prior version of this helper
    // checked `.detail` and silently fell back to the generic message for
    // every single error, live-verified as a real bug during sign-off.
    postMock.mockResolvedValueOnce({
      data: undefined,
      error: {
        error: {
          code: "HTTP_ERROR",
          message: "no LLM provider configured — set GEMINI_API_KEY",
          details: null,
        },
      },
    });

    await expect(analyzeQuestion({ question: "What is BBCA's setup?" })).rejects.toThrow(
      "no LLM provider configured — set GEMINI_API_KEY",
    );
  });

  it("falls back to a generic message when the backend gives no parseable error envelope", async () => {
    postMock.mockResolvedValueOnce({ data: undefined, error: {} });

    await expect(analyzeQuestion({ question: "What is BBCA's setup?" })).rejects.toThrow(
      "analysis request failed",
    );
  });
});

describe("fetchSnapshots", () => {
  it("defaults to page 1 and omits an empty symbol filter", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchSnapshots({ symbol: "" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.symbol).toBeUndefined();
    expect(options.params.query.page).toBe(1);
  });

  it("forwards a real symbol filter", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchSnapshots({ symbol: "BBCA" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.symbol).toBe("BBCA");
  });

  it("throws rather than returning a fabricated empty result on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchSnapshots({})).rejects.toThrow("snapshots request failed");
  });
});

describe("fetchSnapshot", () => {
  it("returns the snapshot on success", async () => {
    const snapshot = { id: "1", response: "answer" };
    getMock.mockResolvedValueOnce({ data: snapshot, error: undefined, response: { status: 200 } });

    await expect(fetchSnapshot("1")).resolves.toEqual(snapshot);
  });

  it("throws NOT_FOUND for an unknown id, distinct from a generic failure", async () => {
    getMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "snapshot not found" },
      response: { status: 404 },
    });

    await expect(fetchSnapshot("nope")).rejects.toThrow("NOT_FOUND");
  });
});
