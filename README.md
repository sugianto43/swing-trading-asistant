# IDX Swing Trading Assistant — Claude Code Package

## Contents
- MASTER-PRD.md
- MASTER-TDD.md
- MASTER-CLAUDE-INSTRUCTIONS.md
- CODING-STANDARDS.md
- QUANT-TRADING-RULES.md
- AI-GUARDRAILS.md
- DECISION-LOG.md
- docs/phase-01..18/PRD.md
- docs/phase-01..18/TDD.md
- prompts/global/*
- prompts/phase-01..18/*

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

## Position & Journal (Phase 7)

Tracks what actually happened — manual executions, derived position state, trading journal, and
performance analytics — `apps/api/app/positions/`. This is bookkeeping of real trades, not a strategy
or a scored/backtested system, so there's no versioned config here the way Phases 3-6 have.

**Long-only.** `Execution.side` is `BUY`/`SELL`: BUY opens/adds to a position, SELL reduces/closes it.
Short-selling isn't modeled — a SELL exceeding the open quantity is rejected outright, never treated
as opening a short. This matches the stated persona (IDX retail swing trader); short-selling isn't
broadly available to that audience.

**Executions are append-only.** No update or delete endpoint exists anywhere for `Execution` rows — a
recording mistake is corrected by entering a new offsetting execution, an explicit adjustment rather
than a silent edit to history. `Position` is a derived/materialized view recomputed by
`ExecutionService` inside the same transaction as every new execution; `Execution` is the source of
truth, never the other way around. At most one non-terminal (`PLANNED`/`OPEN`/`PARTIALLY_CLOSED`)
`Position` per instrument is enforced at the application layer (not a DB constraint, for
SQLite/Postgres portability, same tradeoff made elsewhere in this codebase) — reopening after
`CLOSED`/`CANCELLED` creates a fresh `Position` row rather than reusing the old one.

**Fee apportionment on partial exits**: each SELL apportions the position's cumulative entry fees
pro-rata by `(quantity sold / cumulative quantity ever bought)`, plus its own exit fee in full — see
`position_engine.py`'s docstring for the exact formula. This keeps total fees fully accounted for
exactly once across however many partial exits occur.

**`PLANNED` positions**: `POST /api/v1/positions` creates a position from a `TradePlan` before any
execution happens (`status=PLANNED`, requires the plan be `VALID`, and that the instrument has no
other non-terminal position already). `POST /api/v1/positions/{id}/cancel` moves `PLANNED` →
`CANCELLED` — the only state cancellation is valid from, so an already-executed position can't be
retroactively "cancelled".

**Journal** is ordinary mutable CRUD (unlike executions) — one entry per position, refined as the
trader's thinking evolves. `reference_urls` holds external links only (e.g. a chart screenshot hosted
elsewhere) — **no file upload or storage infrastructure exists in this phase**, so attachments are
references, never uploaded content.

**Performance analytics** (`GET /api/v1/performance/*`) — portfolio equity curve/drawdown/exposure and
unrealized P&L (mark-to-market against the latest available `PriceBar.close`, reused from Phase 2, no
future-data leakage), grouped breakdowns by setup/sector/holding-period/score-bucket. `max_drawdown_pct`
and `sharpe_ratio` are reused directly from `app.backtesting.metrics` (pure functions of an equity
curve, no coupling to simulated trades). **Documented gaps, not silent ones**:
- performance by market regime — no market-wide/breadth data source exists yet (Phase 9 scope, the
  same gap already documented since Phase 4's scanner).
- early-exit/late-entry classification and recurring-mistake pattern detection — these need a
  subjective heuristic the PRD doesn't specify; only clearly-defined, non-subjective behavior metrics
  are computed (`stop_violated`: exit worse than the linked `TradePlan.stop_price`; entry/quantity
  deviation-from-plan percentages).

```bash
python -m app.positions.cli record --symbol BBCA --side BUY --quantity 100 --price 9500 --fee 15000 --executed-at 2024-12-31T09:30:00+07:00
```

API: `POST/GET /api/v1/executions`, `POST /api/v1/positions` (planned), `POST /api/v1/positions/{id}/cancel`,
`GET /api/v1/positions`, `GET /api/v1/positions/{id}`, `POST/GET /api/v1/positions/{id}/journal`,
`GET /api/v1/performance/summary` (`?initial_capital=`), `/by-setup`, `/by-sector`, `/by-holding-period`,
`/by-score-bucket`, `/behavior`. No order-execution path exists anywhere — this only records what a
human already did through their broker.

## AI Analyst (Phase 8)

Grounded AI analysis over the existing domain — `apps/api/app/ai/`. An LLM orchestrator runs a
bounded tool-calling loop against a **provider-agnostic** interface (`LLMProvider`), calling only
**typed, read-only tools** (MASTER-PRD §13) that wrap Phases 2-7's services, then persists a full
audit trail (`AnalysisSnapshot`: model, provider, prompt version, every tool call, the structured
data snapshot, the response, and any guardrail flags — MASTER-PRD §21).

**Provider**: Google Gemini (free tier), via `google-genai` — see `DECISION-LOG.md` ADR-0003 for
the full rationale (personal-use scope, not a production licensing decision). `FixtureLLMProvider`
is deterministic and network-free; **every automated test uses it exclusively** — the real
`GeminiProvider` is never imported or required to run the test suite, and requires
`GEMINI_API_KEY` (env var, never committed) to be constructed at all.

**Typed tools** (`app/ai/tools.py`): `get_stock_snapshot`, `get_technical_snapshot`, `get_setup`,
`get_trade_plan`, `get_backtest`, `get_position`, `get_portfolio_risk`, plus `get_market_regime`/
`get_market_events` which always return `DATA_UNAVAILABLE` — no market-wide/breadth/news data
source exists yet (Phase 9 scope), the same documented-gap discipline as every prior phase's
missing market context. **There is no tool that writes anything, places an order, or runs SQL** —
the "no execution / no risk-limit changes" guardrail (MASTER-PRD §13 Forbidden list) is structural
(the capability doesn't exist in the registry), not just a prompt instruction; a request for a
tool outside the registry is refused by `app/ai/guardrails.py` before it can ever be invoked.

**Prompt injection defense**: every tool result is wrapped and labeled as untrusted data, not
instructions, before being fed back into the prompt (`wrap_tool_result_as_untrusted`) — text
embedded in a journal note or execution note (both free-text, user-authored) cannot be mistaken
for a system instruction just because it flowed through a tool call. The final response is also
scanned for red-flag phrasing (order-placement claims, certainty claims, risk-limit-change claims)
via `scan_response`; flags are recorded on the snapshot for review. **This is defense-in-depth, not
a provable guarantee** — documented honestly, not oversold.

**RAG**: `app/ai/retrieval.py` does lightweight term-overlap scoring over local methodology docs
(`QUANT-TRADING-RULES.md`, `MASTER-PRD.md`) — no vector store or embeddings API, since no such
infra exists yet in this stack (Redis arrives in Phase 10) and the corpus is small enough that
term overlap is sufficient, deterministic, and testable without a network call.

The tool-calling loop is hard-capped (`MAX_TOOL_CALL_ITERATIONS = 6`) to bound cost/latency if a
provider misbehaves.

```bash
python -m app.ai.cli analyze --symbol BBCA --question "What does BBCA's setup look like right now?"
```

API: `POST /api/v1/ai/analyze` (body: `question`, optional `symbol`) — 503 if no provider is
configured (no `GEMINI_API_KEY`); `GET /api/v1/ai/snapshots` (filter: `symbol`),
`GET /api/v1/ai/snapshots/{id}`. Every snapshot is append-only, same discipline as `Execution`.

## Market Intelligence (Phase 9)

Market breadth, sector performance, regime classification, and canonical corporate-action events —
`apps/api/app/intelligence/` — all computed from data already ingested in Phases 2/3, no new vendor.

**Scope decision**: MASTER-PRD §12 lists news/earnings/dividends/corporate-actions/sector-performance/
breadth/macro-events/regulatory-events as things "later phases MAY include," not all mandatory.
yfinance (the only integrated vendor) has no reliable free feed for news, earnings calendars, or
macro/regulatory events on IDX tickers. This phase builds **breadth, sector performance, and regime**
(fully computable from the already-ingested universe) and exposes **corporate actions as canonical
timestamped events**. **News/earnings-calendar/macro/regulatory events are explicitly deferred** — no
viable free data source exists, and inventing one would violate "never invent market data." Documented
gap, not silent (see `DECISION-LOG.md` if a future ADR revisits this).

**Breadth is a proxy for the locally-ingested universe, not the whole IDX market** — regime
classification (`RISK_ON`/`RISK_OFF`/`NEUTRAL`) uses the universe's own `% above SMA50` and
advance/decline counts (`app/intelligence/breadth_engine.py`, `regime_engine.py`), not an external
index (`^JKSE` was considered and deliberately not pursued — see the plan record for this phase).
Thresholds are illustrative starting values (`RegimeConfig`), not a verified market-timing signal —
same caveat as backtesting's fee/slippage defaults.

**Events** (`app/intelligence/event_mapper.py`) are a read-time canonicalization of Phase 2's already-
ingested `CorporateAction` rows — no new ingestion path, no duplicated table. The Critical Rule (TDD):
historical/event-aware queries filter strictly on `announced_at` (the public-availability timestamp),
**never** `ex_date`/`effective_date`, which can be scheduled/known ahead of when an action actually
became public knowledge. When yfinance doesn't supply an announcement timestamp, `ingested_at` is used
as a conservative fallback and `availability_is_estimated=True` flags the substitution explicitly.

Breadth snapshots are idempotent-upsert-by-natural-key (`as_of`, `breadth_version`) — same pattern as
indicators/scanner/trade plans, not an experiment like a backtest run.

Phase 8's `get_market_regime`/`get_market_events` AI tools now consume this service directly instead
of returning a hardcoded `DATA_UNAVAILABLE` stub.

```bash
python -m app.intelligence.cli compute-breadth --date 2024-12-31
```

API: `POST /api/v1/intelligence/breadth/compute` (body: `as_of`), `GET /api/v1/intelligence/breadth`
(`?as_of=`, latest if omitted), `GET /api/v1/intelligence/breadth/history` (`?start=&end=`),
`GET /api/v1/intelligence/sector-performance` (`?as_of=&lookback_days=`),
`GET /api/v1/intelligence/events` (`?symbol=&as_of=` — `as_of` enforces the Critical Rule cutoff).

## Operations (Phase 10 — Production)

Workers, scheduling, alerts, and observability — `apps/api/app/worker/`. Turns the daily
ingestion → indicators → scanner → risk-plans → breadth pipeline (Phases 2–6, 9) plus a new
alert-evaluation stage into something that runs unattended, with failure isolation, duplicate-run
protection, and a way to see whether it's healthy — without executing trades, changing risk limits,
or fabricating data (`AI-GUARDRAILS.md` still applies).

**Stack**: Redis + RQ (task queue) + rq-scheduler (cron), chosen over Celery (too heavy for this
scale) and a bare APScheduler (doesn't provide a distributable job queue). No email/SMS/webhook
alert delivery vendor was introduced — alerts are persisted and queried via API/SSE only. `apps/web`
is untouched; this phase is backend-only.

**Authentication gap**: the API has been unauthenticated since Phase 1. This phase does not add
auth — it's an explicitly deferred, documented gap, not an oversight.

### Job pipeline

Each stage is a plain, directly-testable function in `app/worker/jobs.py` (`run_ingestion`,
`run_indicators`, `run_scanner`, `run_risk_plans`, `run_breadth`, `run_alerts`) that takes an
already-open DB session — no Redis/RQ dependency in the function body. `app/worker/pipeline.py`'s
`enqueue_pipeline()` is the actual unit of work RQ enqueues: it runs all six stages in order for a
symbol universe, each guarded by a distributed lock (`app/worker/locks.py`, keyed on
`(job_type, date)`) so an overlapping/duplicate enqueue is a safe no-op, not a double-run. Every
stage invocation is recorded as a `JobRun` row (`RUNNING`→`SUCCEEDED`/`FAILED`/`PARTIAL`), the same
audit-trail pattern as `IngestionRun`/`ScanRun`/`BacktestRun`.

One symbol's ingestion/indicator failure does not abort the rest of the batch — `run_ingestion` and
`run_indicators` isolate per-symbol failures and roll up to `PARTIAL` (some succeeded) or `FAILED`
(all failed), addressing the TDD's "provider outage" reliability requirement. A second real
market-data vendor to actually fall back to remains out of scope — no viable free alternative to
yfinance was evaluated.

### Alerts

`app/worker/alert_engine.py` (pure functions, no DB access) evaluates: `SETUP_DETECTED`, `BREAKOUT`,
`PRICE_NEAR_ENTRY`/`PRICE_NEAR_STOP`/`PRICE_NEAR_TARGET` (within `AlertConfig.near_price_threshold_pct`,
default 2%), `UNUSUAL_VOLUME` (relative volume ≥ threshold), `STALE_DATA` (makes MASTER-PRD §20's
"do not generate a fresh signal on stale data" visible instead of only silently skipping), and
`IMPORTANT_EVENT` (from Phase 9's corporate-action events). **`SETUP_INVALIDATED` is deliberately
NOT implemented** — Phase 4's `invalidation_conditions` are human-readable strings, not
re-evaluatable predicates, so mechanically detecting invalidation isn't possible without new
setup-detector logic. Documented gap, not fabricated.

Alerts are deduplicated at the DB level — a `UniqueConstraint` on `(alert_type, instrument_id,
trigger_date)`, not just an app-level check — so a re-run of `run_alerts` for the same day never
creates duplicates, including under concurrent job runs. Every newly-persisted alert is published to
a Redis pub/sub channel (`alerts:new`), consumed by `GET /api/v1/alerts/stream` (SSE).

### CLI

```bash
python -m app.worker.cli run-worker [--burst]
python -m app.worker.cli enqueue-pipeline --symbols BBCA,TLKM,ASII --date 2024-12-31
python -m app.worker.cli register-scheduler --symbols BBCA,TLKM,ASII
```

`register-scheduler` registers `enqueue_pipeline` on a daily cron (`30 09 * * 1-5` — 09:30 UTC =
16:30 WIB, after IDX close; expressed in UTC because rq-scheduler evaluates cron against the
process's system clock, which is UTC in the deployed containers) via rq-scheduler; re-registering
(e.g. on process restart) replaces the previous entry instead of creating a duplicate.

`run_risk_plans`'s position sizing uses `Settings.pipeline_capital` (env var `PIPELINE_CAPITAL`,
default `100_000_000.0` IDR — illustrative only, same caveat as the backtesting default) rather than
a backtesting constant, so the scheduled pipeline's real trade plans are sized off a configurable,
explicitly-named capital figure (MASTER-PRD FR-011).

### API

`GET /api/v1/alerts` (`?alert_type=&symbol=&trigger_date=`, paginated), `GET /api/v1/alerts/stream`
(SSE), `GET /api/v1/ops/status` (queue depth, worker count, per-stage freshness/last-status, recent
failure count — read from RQ's own registries and the `JobRun` table, not a separate metrics stack),
`GET /api/v1/ops/job-runs` (`?job_type=&status=`, paginated).

### Docker Compose

`docker compose up` now also starts `redis`, `worker` (`run-worker`), and `scheduler`
(`register-scheduler` + `rqscheduler`) alongside the existing `db`, `api`, `web` services.

### Testing discipline

`fakeredis[lua]` stands in for Redis in all automated tests (the `[lua]` extra is required — redis-py's
`Lock.release()` uses a Lua script via EVALSHA, which plain fakeredis doesn't support). Real
Redis/Postgres are verified live via Docker at sign-off, and CI's `worker-integration` job runs
against a real Redis service container (mirroring `api-migrations`'s Postgres service-container
pattern) to catch anything fakeredis's emulation might miss. `pip-audit` runs in CI as a dependency
vulnerability scan.

### Backups

Documented posture, not automation: Postgres data lives in the `db_data` named volume (Docker
Compose) — back it up with routine `pg_dump`/volume snapshots on whatever schedule the deployment
environment requires. No backup automation is implemented by this phase.

## Release Readiness (Phase 11 — E2E Hardening)

Final phase on the roadmap (MASTER-PRD §23: `1 -> 2 -> ... -> 10 -> 11`). No new features, no new
routes, no new DB schema — this phase validates that everything built across Phases 1-10 actually
composes into the golden end-to-end journey (MASTER-PRD §24), and closes out the two open
questions ("is auth in scope?", "is a frontend E2E test in scope?") that had been implicitly
deferred at every prior phase.

**Scope decisions**: `apps/web` remains the untouched Phase 1 scaffold — it was never built out
across Phases 1-10, and building it now would be new frontend functionality, not hardening.
Authentication is now permanently out of scope for this project (see `DECISION-LOG.md` ADR-0004),
not a gap to keep re-raising — MASTER-PRD's journey ("Human Decision -> Manual Execution") maps
entirely onto existing API calls, none of which require a browser.

### Golden E2E journey test

`apps/api/tests/e2e/test_golden_journey.py` drives the full MASTER-PRD §24 journey — IDX data,
validation, indicators, market context, scanner, ranking, stock analysis, risk, trade plan, AI
explanation, manual execution, position, exit, journal, performance, AI review — against one
shared DB session. Compute stages that have no REST trigger by design (ingestion, indicators,
scanner, and — unlike those three — breadth, which does have `POST /intelligence/breadth/compute`)
run through the real service layer, exactly as the CLI/worker would call them; every
user-actionable stage runs through the real FastAPI routes via `TestClient`. This catches
integration defects a single phase's own isolated tests can't — a schema/field mismatch between
what one stage writes and what the next stage reads.

```bash
python -m pytest -q tests/e2e/
```

### Production smoke test

`scripts/smoke_test.sh` brings up the real `db`/`redis`/`api` containers via Docker Compose, waits
for health, and checks `/api/v1/health`, `/api/v1/instruments` (Postgres-backed), and
`/api/v1/ops/status` (Redis-backed) actually respond — proving the deployed containers can talk to
each other, which nothing in the SQLite/fakeredis-backed `pytest` suite exercises. Tears itself
down on exit.

```bash
./scripts/smoke_test.sh
```

### Rollback procedure

1. **Schema rollback**: `alembic downgrade <previous-revision>` (from `apps/api`, with
   `DATABASE_URL` pointed at the target database) — every migration in this project has a verified
   `downgrade()`, exercised live at every phase's sign-off, most recently migration `0010` in
   Phase 10.
2. **Application rollback**: redeploy the prior image tag for `api`/`worker`/`scheduler` via
   `docker compose up -d` after pointing the compose file (or an env override) at the previous
   tag — no in-place mutation, no data migration required for an application-only rollback.
3. **Data restore** (only if a bad migration already wrote data): restore the `db_data` volume or
   the most recent `pg_dump` backup (see Backups above), then apply step 1 against the restored
   database.

Verified live at Phase 11 sign-off: a real `pg_dump`/restore round-trip and a full
`alembic downgrade base && alembic upgrade head` cycle against a live Postgres container.

## Web Foundation (Phase 12)

`apps/web` moves past the Phase 1 scaffold: app shell, top nav (`Overview` / `Scanner` / `Risk` /
`Positions` / `AI` / `Alerts` — each a stub page until its own phase lands), a typed API client,
and dark/light theming. No real screen content yet — that starts at Phase 13.

**Component layer**: [shadcn/ui](https://ui.shadcn.com) (Radix UI primitives, Nova preset) on top
of the existing Tailwind v4 setup — copy-into-repo components (`src/components/ui/`), not a
runtime dependency. Add more components as later phases need them (`npx shadcn@latest add <name>`).

**Theming**: `next-themes`, system-preference by default, toggle in the nav. Anything that reads
`resolvedTheme` (or similar browser-only state) on first render must gate on
`useHasMounted()` (`src/lib/use-has-mounted.ts`, built on `useSyncExternalStore`) — `resolvedTheme`
resolves synchronously on the client's first render (from `localStorage`/`matchMedia`), so it's
**never** `undefined` in the browser the way it always is during SSR; branching on
"is it still undefined" looks reasonable but causes a real hydration mismatch, caught live via a
browser check while building this phase.

**Typed API client**: `src/lib/api/schema.d.ts` is generated from the backend's OpenAPI schema via
`openapi-typescript`, and **committed** — CI's `web` job never needs a live backend. Regenerate it
whenever the backend's API surface changes:

```bash
# with the backend running (docker compose up -d db api, or uvicorn locally)
npm run generate:api-types
```

`src/lib/api/client.ts` wraps the generated types with `openapi-fetch`. One subtlety:
`NEXT_PUBLIC_API_BASE_URL` already includes the `/api/v1` prefix (established since Phase 1), but
the generated schema's paths embed that same prefix (FastAPI bakes its router prefix into the
OpenAPI document) — so the client derives the request origin from the env var rather than using it
directly as `openapi-fetch`'s `baseUrl`, or every request would resolve to `/api/v1/api/v1/...`.

**Server state**: TanStack Query. This phase's only real backend call: a live `GET /health` status
indicator in the nav (`src/components/layout/api-status.tsx`), proving the client is wired
end-to-end — verified against the real Dockerized backend, not just mocked in tests.

**Known gap fixed this phase**: `vitest.config.mts` only matched `src/**/*.test.tsx`, silently
skipping any plain `.test.ts` file (e.g. the API client's own unit tests) — pre-existing since
Phase 1, never noticed until a non-component test actually needed to run.
