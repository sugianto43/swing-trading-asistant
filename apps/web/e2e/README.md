# Web E2E (Phase 18)

Golden-journey, accessibility, and error-rendering checks driving the real UI (Playwright +
`@axe-core/playwright`), against a real Docker backend. Not run in CI (no Docker there) — a
local/manual gate, matching the discipline every phase's sign-off has already used this project,
now formalized into a committed, reproducible spec instead of a scratchpad script.

- `golden-journey.spec.ts` — MASTER-PRD §24's happy path, with an axe check at every step.
- `a11y.spec.ts` — the routes the journey doesn't naturally visit (`/`, `/alerts`, `/risk/[id]`,
  `/ai/[id]`), completing axe coverage across all 13 real routes.
- `error-rendering.spec.ts` — "no client-side fabrication" (Phase 18 TDD's audit item):
  live-verifies a genuine backend failure (overselling) renders the backend's real message, not a
  fabricated/generic one. This is the E2E-level regression guard for the `positions.ts` bug this
  phase's own implementation found and fixed — a unit test mocking the wrong envelope shape would
  pass regardless of whether the real parsing logic works, which is exactly what happened before.

## Prerequisites

1. Backend up: `docker compose up -d db redis api` (from the repo root).
2. Seed real data: `./e2e/seed.sh` (from `apps/web`) — ingests BBCA, computes indicators, and
   produces a real BREAKOUT scan candidate the journey needs to build a trade plan against.
3. Web app running against that backend:
   - For iteration: `npm run dev` (or `docker compose up -d web`, which builds the `dev` Dockerfile
     stage and hot-reloads exactly as before Phase 18).
   - For the release-readiness check specifically: build and serve the **production** artifact —
     `npm run build && npm run start` — since the golden journey is meant to validate what actually
     ships, not just the dev server. `docker build --target runner .` builds the same thing as a
     container image.

## Running

```sh
npx playwright test          # everything
npx playwright test e2e/golden-journey.spec.ts
npx playwright test e2e/a11y.spec.ts
```

## AI steps

The golden journey's AI-explanation and AI-review steps assert only that the request reaches a
settled, definitive state — not which specific outcome it lands in. All of the following are valid,
correctly-un-fabricated responses, and the spec accepts any of them:

- A real grounded answer, if `GEMINI_API_KEY` is configured in the Docker `api` service's
  environment.
- The plain `"no LLM provider configured — set GEMINI_API_KEY..."` message, if no key is
  configured. This was Phase 16's own sign-off precedent — a plainly-rendered 503 is a correct
  outcome, not a failure to route around.
- A transient upstream failure (e.g. the provider itself returning 503 under load) — seen live
  during this phase's own audit. The UI rendered the backend's real error message verbatim, exactly
  as designed; the E2E spec's job is to prove that happens, not to assert a specific happy path a
  free-tier LLM API can't guarantee on every run.

A real key is optional. If you have one, add it to the repo-root `.env`
(`GEMINI_API_KEY=...`) and `docker compose up -d api` to pick it up — `docker-compose.yml`'s `api`
service already forwards it.

## Performance budget

`npm run build`'s production output is the source of truth. As of this phase: total
`.next/static` (all client JS + CSS, all routes combined) is ~1.6 MB. Documented budget: **stays
under 2 MB**. Re-check with `du -sh .next/static` after `npm run build` if this ever needs
revisiting — this is a bundle-size proxy (Next 16's Turbopack build no longer prints a per-route
size table to stdout the way older Next versions did), not a full Lighthouse audit (runtime/paint
timing, accessibility scoring beyond axe, etc.) — an accepted, documented trade-off for this
project's personal-use scale, not a silent substitution.

## Docker production smoke test

Verifies the actual production artifact serves correctly, not just `next dev`:

```sh
cd apps/web
docker build --target runner -t swing-web-prod .
docker run -d -p 3002:3000 -e NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 --name swing-web-prod swing-web-prod
curl -sf http://localhost:3002/overview   # 200
docker rm -f swing-web-prod && docker rmi swing-web-prod
```
