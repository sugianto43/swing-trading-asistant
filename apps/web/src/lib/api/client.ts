import createClient from "openapi-fetch";

import type { paths } from "./schema";

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

/**
 * NEXT_PUBLIC_API_BASE_URL already includes the /api/v1 prefix (see
 * .env.example / docker-compose.yml — established since Phase 1), but the
 * generated schema's paths embed that same prefix (FastAPI's router
 * prefix is baked into the OpenAPI document). openapi-fetch's baseUrl
 * must be the origin only, or every request would resolve to
 * /api/v1/api/v1/... — so the origin is derived here rather than
 * changing the env var's established meaning.
 */
export function apiOrigin(baseUrl: string = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL): string {
  return new URL(baseUrl).origin;
}

export const apiClient = createClient<paths>({ baseUrl: apiOrigin() });
