# IDX Swing Trading Assistant — Claude Code Package

## Contents
- MASTER-PRD.md
- MASTER-TDD.md
- MASTER-CLAUDE-INSTRUCTIONS.md
- CODING-STANDARDS.md
- QUANT-TRADING-RULES.md
- AI-GUARDRAILS.md
- DECISION-LOG.md
- docs/phase-01..11/PRD.md
- docs/phase-01..11/TDD.md
- prompts/global/*
- prompts/phase-01..11/*

## Recommended Claude Code Workflow

For each phase:

1. Read the master files.
2. Run `prompts/phase-XX/plan.md`.
3. Review/approve the plan.
4. Run `prompts/phase-XX/implement.md`.
5. Run `prompts/phase-XX/test.md`.
6. Run `prompts/phase-XX/review.md`.
7. Approve fixes.
8. Run `prompts/phase-XX/fix.md`.
9. Run `prompts/phase-XX/sign-off.md`.
10. Only proceed when status is PROCEED.

## Example

```text
Read docs/MASTER-PRD.md
Read docs/phase-03/PRD.md
Read docs/phase-03/TDD.md
Read prompts/phase-03/plan.md

Execute the planning workflow only.
Do not modify code.
```

Then, after approval:

```text
Read prompts/phase-03/implement.md
Execute the Phase 3 implementation workflow.
```

## Important
These files define engineering requirements. Actual IDX data-provider selection must separately verify licensing, API terms, historical depth, latency, and redistribution rights.

## Local Development (Phase 1 — Foundation)

### Prerequisites
- Docker + Docker Compose
- Python 3.12+ (for running API tooling outside Docker)
- Node 22+ (for running web tooling outside Docker)

### Run everything with Docker Compose
```bash
cp .env.example .env
docker compose up --build
```
- API: http://localhost:8000/api/v1/health
- Web: http://localhost:3000

### API (apps/api) — local, without Docker
```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# quality gates
ruff format . && ruff check . && mypy app && pytest -q
```

### Web (apps/web) — local, without Docker
```bash
cd apps/web
npm ci
npm run dev

# quality gates (build before tsc: Next.js generates route types during build)
npm run lint && npm run build && npx tsc --noEmit && npm test
```

### CI
`.github/workflows/ci.yml` runs API lint/type-check/tests, an Alembic migration up/down check against a real Postgres service container, and web lint/type-check/test/build on every push and pull request.

## Market Data Ingestion (Phase 2)

Two provider implementations exist behind the same `MarketDataProvider` interface
(`apps/api/app/marketdata/provider.py`):

- **`fixture`** — deterministic, network-free. Used by all automated tests. No data unless you
  inject it (see `FixtureProvider` constructor args) or use it programmatically.
- **`yfinance`** — adapter over the unofficial `yfinance` package. Personal/non-commercial use
  only; see `DECISION-LOG.md` ADR-0002 for the full rationale and known limitations (no IDX
  instrument-master or trading-calendar API — those are backed by a local seed and observed
  trading days respectively).

Run ingestion via the CLI (from `apps/api`, with the DB migrated and `DATABASE_URL` pointing at
your Postgres instance, or via `docker compose exec api ...`):

```bash
python -m app.marketdata.cli ingest --provider yfinance --symbols BBCA,BBRI,BMRI --start 2024-01-01 --end 2024-12-31
```

This syncs the instrument universe from the local seed
(`apps/api/app/marketdata/seed/idx_instruments.csv`), then ingests OHLCV and corporate actions for
each symbol. Re-running is safe — ingestion is idempotent (upsert by natural key, no duplicate
rows). Invalid/stale/suspect data is marked via `quality_status`, never silently dropped.

Read-only API endpoints: `GET /api/v1/instruments`, `/instruments/{symbol}`,
`/instruments/{symbol}/prices` (add `?adjusted=true` for split-adjusted prices — dividend/
total-return adjustment is not implemented), `/instruments/{symbol}/corporate-actions`,
`/calendar`.
