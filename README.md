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

## Technical Indicators (Phase 3)

Canonical indicators (SMA20/50/200, EMA20/50, RSI14, ATR14, MACD, Bollinger Bands, volume SMA,
relative volume, rolling high/low, returns, volatility) are computed by `apps/api/app/indicators/`
— plain Python, not pandas/numpy, so every formula is auditable in one place
(`app/indicators/calculations.py`). Indicators are computed from split-adjusted, `VALID`/`SUSPECT`
price bars only (`INVALID` bars are excluded, same as a missing session).

Compute and persist indicator snapshots (after market data has been ingested — see above):

```bash
python -m app.indicators.cli compute --symbols BBCA,BBRI,BMRI --start 2024-01-01 --end 2024-12-31
```

Snapshots are versioned (`app/indicators/versioning.py`'s `INDICATOR_VERSION`) so historical
results stay traceable to the exact formula/parameter set that produced them — bump the version
string, never redefine what an existing version means. Re-running is idempotent.

Read-only API endpoint: `GET /api/v1/instruments/{symbol}/indicators`.

## Swing Scanner (Phase 4)

Five canonical setups (breakout, pullback continuation, momentum continuation, moving-average
reclaim, volatility contraction → expansion) detected against Phase 3's indicator snapshots —
`apps/api/app/scanner/setups/`. Each is a pure function with documented prerequisites, qualifying
conditions, and invalidation conditions. Qualifying setups get a 7-component explainable score
(trend, momentum, volume, price structure, volatility, setup quality, risk/reward — weights and
thresholds versioned in `app/scanner/scoring_config.py`'s `SCORE_VERSION`).

**Market context/regime is intentionally absent** — no market-wide/breadth data source exists yet
(Phase 9 scope); omitting it is a documented gap, not a fabricated placeholder.

Symbols with stale price data (per Phase 2's freshness check) are skipped, not scored — the skip
is recorded in a `scan_runs` audit row, never silent.

```bash
python -m app.scanner.cli scan --symbols BBCA,BBRI,BMRI --date 2024-12-31
```

Read-only API endpoints: `GET /api/v1/scanner/candidates` (filters: `sector`, `setup`, `min_score`,
`scan_date`; sort: `score`, `momentum`, `risk_reward`, `volume_score`) and
`GET /api/v1/instruments/{symbol}/candidates`.

Risk/reward here is a **ranking heuristic only** (ATR-based stop, structure- or ATR-projected
target) — not a trade plan. Phase 6 owns real position sizing.
