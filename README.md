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

## Backtesting (Phase 5)

Reproducible historical simulation over `ScanCandidate` signals — `apps/api/app/backtesting/`.
Entry fills at the next trading day's open (`NEXT_OPEN`, the only non-leaking execution model given
signals are computed EOD), stop/target derived from ATR at entry, a same-bar stop+target conflict
resolved conservatively (**stop wins**), fixed-fractional position sizing (lot-aware, distinct from
Phase 6's full risk engine), and fee/slippage costs applied to every fill.

**Survivorship bias:** eligibility is checked against `Instrument.listing_date`/`delisting_date`
(the actual exchange dates), not `InstrumentStatusHistory` alone — that table is stamped at
ingestion wall-clock time, so relying on it alone would make every date before your first ingestion
run look "not yet listed" and silently produce zero trades for any realistic historical backtest.
`InstrumentStatusHistory` still refines the baseline for status changes observed during live
operation (e.g. a suspension detected while the system was running).

Each invocation creates a **new** `backtest_runs` row rather than upserting — a backtest is an
experiment to compare (same config re-run for reproducibility, or different configs side by side),
not data to keep in sync like ingestion/indicators/scanner.

`scan_candidates` must already exist for the date range — run the scanner across each historical
day first (a real backfill, not a single "as of today" scan):

```bash
python -m app.backtesting.cli run --setup BREAKOUT --start 2024-01-01 --end 2024-12-31
```

Read-only API: `GET /api/v1/backtests`, `/backtests/{id}` (includes metrics), `/backtests/{id}/trades`,
`/backtests/{id}/equity-curve`.

**Known limitation:** reproducibility means identical config + identical underlying DB state →
identical results — there is no separate frozen dataset-snapshot system (an open MASTER-PRD
decision), so results can change if you re-ingest/re-adjust historical data later.

## Risk & Trade Plan (Phase 6)

Deterministic risk engine — `apps/api/app/risk/` — that converts a qualifying scanner setup into
an entry-zone/stop/targets/position-size trade plan, enforcing configurable portfolio risk limits.
Pure Python, versioned (`RiskConfig.risk_version`, bumped in `app/risk/config.py` whenever a
default/formula changes), same auditability discipline as indicators/scanner/backtesting.

Entry zone is a small buffer above the latest close; stop/targets are ATR-based (`stop_atr_multiplier`,
`target_atr_multiplier`); position size is fixed-fractional, lot-aware, and accounts for slippage and
fees so a plan's quantity never overstates what capital can actually afford. A plan is rejected
(`status=REJECTED`, `rejection_reasons` populated) rather than silently dropped or downsized whenever
it violates a configured limit (invalid stop, R:R, liquidity, position/portfolio/sector allocation,
concurrent-position count) — every configured limit is checked and reported, not just the first
violation.

**Portfolio state is caller-supplied, not persisted.** Phase 7 (Position & Journal) — which will hold
real open positions — has not been built yet, so `existing_positions` is an explicit input to each
plan request (a list of `{symbol, sector, allocation_amount}`), never a fabricated or assumed table.
Omitting it means "no existing positions," a valid case, not a placeholder.

**AI cannot modify risk limits**: `RiskConfig` limits are code/deploy-time values only, never exposed
through any mutating API — that's guaranteed by construction (no PUT/PATCH endpoint exists), not by an
access-control check on top of one.

A trade plan is keyed by `(instrument, plan_date, setup_type, risk_version)` and idempotently
upserted — unlike a `BacktestRun` (an experiment, always a new row), re-running a plan for the same
day/config updates the existing row, since a plan is meant to reflect the current best answer for that
day, not a comparison across runs.

```bash
python -m app.risk.cli plan --symbol BBCA --setup BREAKOUT --date 2024-12-31 --capital 100000000
```

Read-only/compute API: `POST /api/v1/risk/trade-plans` (creates/updates a plan; body includes
`existing_positions` and `capital`), `GET /api/v1/risk/trade-plans` (filters: `symbol`, `setup_type`,
`status`, `plan_date`), `GET /api/v1/risk/trade-plans/{id}`. No execution path exists anywhere in this
phase — a trade plan is a number on screen, never an order.
