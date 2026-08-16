import { afterEach, describe, expect, it, vi } from "vitest";

import { apiOrigin } from "./client";
import createClient from "openapi-fetch";
import type { paths } from "./schema";

describe("apiOrigin", () => {
  it("strips the /api/v1 path, keeping only the origin", () => {
    expect(apiOrigin("http://localhost:8000/api/v1")).toBe("http://localhost:8000");
  });

  it("handles a bare origin with no path", () => {
    expect(apiOrigin("http://localhost:8000")).toBe("http://localhost:8000");
  });

  it("preserves a non-default port", () => {
    expect(apiOrigin("https://api.example.com:9443/api/v1")).toBe("https://api.example.com:9443");
  });

  it("falls back to NEXT_PUBLIC_API_BASE_URL when no argument is given", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://staging.example.com/api/v1");
    expect(apiOrigin()).toBe("https://staging.example.com");
    vi.unstubAllEnvs();
  });

  it("falls back to the hardcoded default when the env var is unset", () => {
    // vi.stubEnv only accepts string values (an empty string is not the
    // same as unset — `??` doesn't treat "" as nullish, so it would
    // throw on new URL("") instead of falling back); deleting the key
    // is what actually reproduces "unset".
    const original = process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    try {
      expect(apiOrigin()).toBe("http://localhost:8000");
    } finally {
      if (original !== undefined) process.env.NEXT_PUBLIC_API_BASE_URL = original;
    }
  });

  it("throws on a malformed URL rather than silently returning something wrong", () => {
    expect(() => apiOrigin("not-a-url")).toThrow();
  });
});

describe("apiClient requests", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("GET resolves against the origin, not the /api/v1-prefixed base URL", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const client = createClient<paths>({ baseUrl: apiOrigin("http://localhost:8000/api/v1") });
    const { error } = await client.GET("/api/v1/health");

    expect(error).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const requestUrl = fetchMock.mock.calls[0][0] as Request;
    expect(requestUrl.url).toBe("http://localhost:8000/api/v1/health");
  });

  it("surfaces a non-2xx response as an error, never as silently-ok data", async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ error: "boom" }), { status: 500 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = createClient<paths>({ baseUrl: apiOrigin("http://localhost:8000/api/v1") });
    const { data, error } = await client.GET("/api/v1/health");

    expect(data).toBeUndefined();
    expect(error).toBeDefined();
  });

  it("propagates a network failure instead of swallowing it", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("network down");
    });
    vi.stubGlobal("fetch", fetchMock);

    const client = createClient<paths>({ baseUrl: apiOrigin("http://localhost:8000/api/v1") });
    await expect(client.GET("/api/v1/health")).rejects.toThrow("network down");
  });
});
