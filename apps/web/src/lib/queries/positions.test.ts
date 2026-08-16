import { describe, expect, it, vi } from "vitest";

const getMock = vi.fn();
const postMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiClient: {
    GET: (...args: unknown[]) => getMock(...args),
    POST: (...args: unknown[]) => postMock(...args),
  },
}));

import {
  fetchExecutions,
  fetchJournal,
  fetchPosition,
  fetchPositions,
  recordExecution,
  upsertJournal,
} from "./positions";

const EXECUTION_PAYLOAD = {
  symbol: "BBCA",
  side: "BUY" as const,
  quantity: 100,
  price: 1050,
  fee: 500,
  executed_at: "2024-03-01T02:30:00.000Z",
};

describe("recordExecution", () => {
  it("returns the resulting position on success", async () => {
    const position = { id: "1", status: "OPEN" };
    postMock.mockResolvedValueOnce({ data: position, error: undefined });

    await expect(recordExecution(EXECUTION_PAYLOAD)).resolves.toEqual(position);
  });

  it("throws the backend's own detail message on a genuine failure (e.g. overselling)", async () => {
    postMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "cannot sell 100 shares, only 50 open" },
    });

    await expect(recordExecution(EXECUTION_PAYLOAD)).rejects.toThrow(
      "cannot sell 100 shares, only 50 open",
    );
  });

  it("falls back to a generic message when the backend gives no detail", async () => {
    postMock.mockResolvedValueOnce({ data: undefined, error: {} });

    await expect(recordExecution(EXECUTION_PAYLOAD)).rejects.toThrow("execution request failed");
  });
});

describe("fetchExecutions", () => {
  it("scopes the request to a single position", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchExecutions("pos-1");

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.position_id).toBe("pos-1");
  });

  it("throws rather than returning a fabricated empty list on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchExecutions("pos-1")).rejects.toThrow("executions request failed");
  });
});

describe("fetchPositions", () => {
  it("defaults to page 1 and omits an empty symbol filter", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchPositions({ symbol: "" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.symbol).toBeUndefined();
    expect(options.params.query.page).toBe(1);
  });

  it("forwards a status filter", async () => {
    getMock.mockResolvedValueOnce({ data: { items: [], total: 0 }, error: undefined });

    await fetchPositions({ status: "OPEN" });

    const [, options] = getMock.mock.calls[0];
    expect(options.params.query.status).toBe("OPEN");
  });

  it("throws rather than returning a fabricated empty result on failure", async () => {
    getMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(fetchPositions({})).rejects.toThrow("positions request failed");
  });
});

describe("fetchPosition", () => {
  it("throws NOT_FOUND for an unknown id, distinct from a generic failure", async () => {
    getMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "position not found" },
      response: { status: 404 },
    });

    await expect(fetchPosition("nope")).rejects.toThrow("NOT_FOUND");
  });
});

describe("fetchJournal", () => {
  it("returns null for a position with no journal yet, not an error", async () => {
    getMock.mockResolvedValueOnce({
      data: undefined,
      error: { detail: "journal entry not found" },
      response: { status: 404 },
    });

    await expect(fetchJournal("pos-1")).resolves.toBeNull();
  });

  it("returns the journal entry when one exists", async () => {
    const journal = { id: "j1", position_id: "pos-1", thesis: "breakout continuation" };
    getMock.mockResolvedValueOnce({ data: journal, error: undefined, response: { status: 200 } });

    await expect(fetchJournal("pos-1")).resolves.toEqual(journal);
  });
});

describe("upsertJournal", () => {
  it("returns the saved journal entry", async () => {
    const journal = { id: "j1", position_id: "pos-1", thesis: "updated thesis" };
    postMock.mockResolvedValueOnce({ data: journal, error: undefined });

    await expect(upsertJournal("pos-1", { thesis: "updated thesis" })).resolves.toEqual(journal);
  });

  it("throws rather than silently discarding a failed save", async () => {
    postMock.mockResolvedValueOnce({ data: undefined, error: { detail: "boom" } });

    await expect(upsertJournal("pos-1", {})).rejects.toThrow("journal upsert failed");
  });
});
