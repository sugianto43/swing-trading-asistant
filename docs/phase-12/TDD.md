# Phase 12 — Technical Design Document

## Architecture
Next.js (App Router) + React + TypeScript + Tailwind CSS, consuming `apps/api`'s existing FastAPI backend (all 11 backend phases). TanStack Query (or equivalent) for server state/caching. A typed API client layer wrapping `fetch` against the backend's OpenAPI schema (`GET /openapi.json`), so every subsequent phase's screens call typed functions, not raw fetch calls scattered across components.

## Required Interfaces
- Typed API client (base URL from `NEXT_PUBLIC_API_BASE_URL`, already read by the existing scaffold).
- Shared layout component: top-level navigation shell with placeholder routes for Overview, Scanner, Risk, Positions, AI, Alerts (built out in later phases — this phase only establishes the shell and routing, not the screens' content).
- Environment configuration matching `docker-compose.yml`'s existing `web` service env.

## Data
None new — this phase adds no backend calls beyond a health check to prove the client is wired correctly end-to-end.

## Tests
Component render tests (Vitest + Testing Library, already scaffolded), API client unit tests (mocked fetch — success, error, network-failure paths), `npm run build`/`lint`/`tsc --noEmit` all clean.
