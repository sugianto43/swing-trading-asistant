# IDX Swing Trading Assistant — Master PRD

**Version:** 1.0  
**Market:** Indonesia Stock Exchange (IDX/BEI)  
**Primary use case:** Weekly swing trading  
**Execution model:** Manual / decision-support only  
**Automated order execution:** Out of scope

## 1. Product Vision

Build a decision-support application that turns IDX market data into a transparent weekly swing-trading workflow:

```text
Market Data
→ Validation
→ Technical Indicators
→ Market/Sector Context
→ Swing Setup Detection
→ Candidate Ranking
→ Risk Analysis
→ Trade Plan
→ AI Explanation
→ Manual Execution
→ Position Monitoring
→ Journal
→ Performance Review
```

The system is an assistant, not an autonomous trading system.

## 2. Problem Statement

A swing trader must manually inspect many stocks, calculate indicators, identify setups, compare candidates, calculate position size, assess risk, review historical performance, and maintain a journal. This creates inconsistent analysis, excessive manual work, emotional decision-making, and difficulty reproducing decisions.

The product reduces this friction while keeping the trader in control.

## 3. Goals

1. Maintain an IDX stock universe.
2. Ingest and validate historical/current market data.
3. Calculate canonical technical indicators.
4. Scan for weekly swing setups.
5. Transparently rank candidates.
6. Generate deterministic trade plans.
7. Calculate risk and position sizing.
8. Backtest strategies without look-ahead bias.
9. Track manual positions.
10. Maintain a trading journal.
11. Analyze portfolio/trading performance.
12. Provide grounded AI explanations.
13. Make important decisions auditable and reproducible.

## 4. Non-Goals

The MVP will not:
- automatically place orders
- act as a broker
- guarantee profits
- replace professional financial advice
- provide unrestricted autonomous trading
- allow AI to execute trades
- become a high-frequency trading platform

## 5. Target User

A self-directed trader focusing on Indonesian equities and typically holding positions for several days to several weeks.

Typical workflow:

```text
Weekend/Evening
→ Review market
→ Run scanner
→ Review candidates
→ Build watchlist
→ Create trade plans
→ Monitor
→ Manual execution
→ Track position
→ Exit
→ Journal
→ Review
```

## 6. Product Principles

### Transparency
Every signal must have an explainable score breakdown and reasons.

### Deterministic Quantitative Logic
The same dataset, strategy version, parameters, execution model, and cost model must reproduce the same result.

### Data Integrity First
Incorrect market data or biased backtests are more dangerous than missing features.

### AI Is Not the Source of Truth
AI explains structured domain data. It must never invent prices, indicators, news, or backtest results.

### Human in the Loop
The user remains responsible for final decisions and execution.

## 7. Core Functional Requirements

### FR-001 Instrument Universe

Maintain IDX instruments with:
- symbol
- company name
- sector/subsector
- listing status
- trading status
- currency
- relevant identifiers

Historical universe membership must be timestamp-aware for historical research.

### FR-002 Market Data

Use an abstract market-data provider interface supporting:
- daily OHLCV
- historical prices
- latest quote where licensed
- corporate actions
- trading calendar

Provider-specific logic must not leak into domain logic.

### FR-003 Data Validation

Validate:
- missing values
- invalid OHLC relationships
- duplicate candles
- timestamps
- impossible prices
- abnormal volume
- missing sessions
- stale data

Invalid data must be marked, not silently accepted.

### FR-004 Technical Engine

Initial canonical indicators:
- SMA20/50/200
- EMA20/50
- RSI14
- ATR14
- MACD
- Bollinger Bands
- volume SMA
- relative volume
- rolling high/low
- returns
- volatility

Calculations must be deterministic, timestamp-safe, and have explicit warm-up behavior.

### FR-005 Swing Setup Detection

Initial setups:
1. Breakout
2. Pullback continuation
3. Momentum continuation
4. Moving-average reclaim
5. Volatility contraction → expansion

Each setup must define prerequisites, qualifying conditions, invalidation conditions, scoring components, and data requirements.

### FR-006 Candidate Scoring

Candidate scoring may include:
- trend
- momentum
- volume
- price structure
- volatility
- setup quality
- risk/reward
- market context

Scores must be configurable, explainable, and versioned.

A score is a ranking heuristic, not a probability of profit.

### FR-007 Watchlists

Users can create, edit, sort, annotate, and pin symbols/watchlists.

### FR-008 Stock Detail

Show:
- price chart
- OHLCV
- indicators
- setup
- score
- support/resistance
- volatility
- sector context
- event/news context when available
- backtest information
- risk analysis
- AI analysis

### FR-009 Trade Plan

A plan contains:
- symbol
- setup
- entry zone
- stop
- targets
- position size
- allocation
- maximum loss
- R:R
- assumptions
- invalidation conditions
- timestamp
- strategy/configuration version

### FR-010 Risk Management

Support configurable:
- maximum risk per trade
- maximum portfolio exposure
- maximum position allocation
- maximum sector exposure
- minimum R:R
- minimum liquidity
- maximum concurrent positions

AI cannot change these limits.

### FR-011 Position Sizing

Sizing considers:
- portfolio capital
- risk percentage
- entry
- stop
- lot size
- fees
- slippage

Invalid plans must be rejected.

### FR-012 Backtesting

Support:
- historical dataset
- strategy version
- parameters
- execution model
- fees
- slippage
- position sizing
- trade ledger
- equity curve

Metrics:
- total return
- CAGR where appropriate
- win rate
- average win/loss
- expectancy
- profit factor
- maximum drawdown
- Sharpe where appropriate
- trade count
- holding period
- R distribution

## 8. Critical Backtesting Integrity

### No Look-Ahead Bias

At timestamp T, calculations may use only information available at or before T.

### No Data Leakage

Future values must never enter indicators, setups, scoring, sizing, portfolio state, or AI analysis.

### Survivorship Bias

Historical tests must account for historical universe membership when applicable.

### Corporate Actions

Splits, dividends, and other corporate actions must be handled consistently and traceably.

### Execution Timing

The engine must explicitly define same-close, next-open, or another configured execution model. No implicit assumptions.

## 9. Positions and Manual Execution

Users can record manual executions containing:
- symbol
- side
- quantity
- price
- timestamp
- fee
- notes

Position states:

```text
PLANNED
OPEN
PARTIALLY_CLOSED
CLOSED
CANCELLED
```

No automatic order execution.

## 10. Trading Journal

Support:
- trade thesis
- setup
- market context
- execution quality
- behavioral notes
- plan adherence
- mistakes
- lessons
- attachments/screenshots where supported

## 11. Performance Analytics

Portfolio:
- equity curve
- drawdown
- exposure
- realized P&L
- unrealized P&L

Strategy:
- performance by setup
- sector
- market regime
- holding period
- score bucket

Trader behavior:
- plan adherence
- early exits
- late entries
- stop violations
- recurring mistakes

## 12. Market Intelligence

Later phases may include:
- news
- earnings
- dividends
- corporate actions
- sector performance
- market breadth
- macro events
- regulatory events

Historical analysis must use information available at the historical decision time.

## 13. AI Analyst

### Allowed
- explain setups
- summarize grounded stock data
- compare candidates
- explain indicators
- explain backtest results
- review completed trades
- summarize market context

### Forbidden
- place orders
- modify risk limits
- fabricate market information
- fabricate backtest results
- claim certainty
- access unrestricted SQL

### Typed Tools

Example tools:
```text
get_stock_snapshot(symbol)
get_technical_snapshot(symbol)
get_setup(symbol)
get_trade_plan(symbol)
get_backtest(strategy_id)
get_position(symbol)
get_portfolio_risk()
get_market_regime()
get_market_events(symbol)
```

Important AI analyses should persist the model/provider, prompt/version, tool inputs, structured data snapshot, response, and timestamp.

## 14. Dashboard

Initial dashboard:

```text
Market Overview
→ Top Swing Candidates
→ Watchlist
→ Open Positions
→ Risk
→ Alerts
→ Journal / Performance
```

## 15. Scanner

Filters:
- universe
- sector
- liquidity
- price
- setup
- minimum score
- trend
- volume
- volatility
- market regime

Sort by:
- score
- liquidity
- momentum
- risk/reward
- relative volume

## 16. Alerts

Potential alerts:
- setup detected
- breakout
- price near entry
- price near stop
- price near target
- setup invalidated
- unusual volume
- stale data
- important event

Alerts must be deduplicated.

## 17. High-Level Architecture

```text
Data Providers
      ↓
Ingestion
      ↓
Validation / Quality
      ↓
Canonical Data
      ↓
Technical Engine ──→ Market Intelligence
      ↓
Scanner
      ↓
Risk Engine
      ↓
Trade Plan
      ↓
Human ──→ Manual Broker Execution
      ↓
Positions
      ↓
Journal
      ↓
Performance

AI sits above the domain layer and consumes approved typed tools.
```

## 18. Suggested Technical Stack

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS
- charting library
- TanStack Query or equivalent

### Backend
- FastAPI
- Python
- Pydantic
- SQLAlchemy
- Alembic

### Database
- PostgreSQL

### Cache/Jobs
- Redis
- worker/scheduler system

### Analytics
- Pandas
- NumPy
- technical-analysis implementation
- Backtrader behind an abstraction where appropriate

### AI
Provider-agnostic LLM layer with typed tools.

## 19. Security

Required:
- secure secret management
- authentication/authorization
- input validation
- rate limiting where appropriate
- audit logging
- safe error responses
- no API keys in source control
- no arbitrary SQL from AI
- prompt-injection defenses
- dependency scanning

## 20. Reliability and Observability

Monitor:
- API latency
- error rates
- ingestion freshness
- provider failures
- queue depth
- worker failures
- scanner execution time
- database health
- AI tool failures
- alert delivery

Handle:
- provider outage
- stale data
- duplicate ingestion
- duplicate jobs
- worker crashes
- DB/Redis failures
- partial processing

When market data is stale or invalid:

```text
DO NOT generate a fresh trading signal.
```

## 21. Auditability and Versioning

Important records retain:
- source
- timestamp
- calculation/version
- strategy version
- parameters
- user action
- AI snapshot
- trade execution history

Version:
- strategies
- scoring models
- indicator configurations
- risk configurations
- backtest configurations
- AI prompts/tool schemas

Historical results must be traceable to the exact configuration that generated them.

## 22. 18-Phase Roadmap

### Phase 1 — Foundation
Repository, app skeleton, configuration, DB, migrations, API conventions, testing, CI.

### Phase 2 — Market Data
IDX instruments, OHLCV, provider abstraction, validation, corporate actions, calendar, lineage.

### Phase 3 — Technical Engine
Canonical indicators and derived features.

### Phase 4 — Swing Scanner
Setup detection and transparent candidate scoring.

### Phase 5 — Backtesting
Historical simulation, execution model, costs, slippage, metrics, validation.

### Phase 6 — Risk & Trade Plan
Risk engine, position sizing, entry/stop/target, portfolio constraints.

### Phase 7 — Position & Journal
Manual execution tracking, positions, journal, performance.

### Phase 8 — AI Analyst
Grounded AI, domain tools, snapshots, guardrails.

### Phase 9 — Market Intelligence
Events, news, fundamentals, sectors, breadth, event-aware analysis.

### Phase 10 — Production
Workers, Redis, scheduling, alerts, observability, reliability, deployment.

### Phase 11 — E2E Hardening
End-to-end, security, quantitative audit, AI audit, disaster recovery, release readiness.

### Phase 12 — Web Foundation
Next.js app shell, layout/navigation, typed API client, environment configuration, CI wiring.

### Phase 13 — Market Overview & Scanner UI
Market overview, top swing candidates, watchlist, instrument detail with indicators.

### Phase 14 — Risk & Trade Plan UI
Build and review trade plans; transparent rejection reasons.

### Phase 15 — Positions, Journal & Performance UI
Manual execution recording, open positions, journal, performance dashboards.

### Phase 16 — AI Analyst UI
Chat/analyze interface, guardrail-flag and DATA_UNAVAILABLE transparency, AI review.

### Phase 17 — Alerts & Realtime UI
Alerts list, SSE live updates.

### Phase 18 — Web E2E Hardening
Golden end-to-end journey through the real UI, accessibility, performance budget, release readiness.

## 23. Phase Dependency

```text
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18
```

Do not implement future-phase functionality prematurely.

## 24. Golden End-to-End Journey

```text
IDX Data
→ Validation
→ Indicators
→ Market Context
→ Scanner
→ Ranking
→ Stock Analysis
→ Risk
→ Trade Plan
→ AI Explanation
→ Human Decision
→ Manual Execution
→ Position
→ Exit
→ Journal
→ Performance
→ AI Review
```

## 25. Product-Level Definition of Done

Release readiness requires:
- critical requirements implemented
- critical tests passing
- quantitative integrity reviewed
- no critical look-ahead/data leakage issue
- market-data lineage available
- deterministic risk controls
- AI guardrails tested
- no automated trading path
- observability operational
- backups/recovery tested
- security review complete
- golden E2E journey passing

## 26. Success Metrics

Measure:
- scanner reliability
- data freshness
- validation error rate
- API reliability
- critical-domain test coverage
- backtest reproducibility
- alert reliability
- AI grounding
- workflow completion

Do not define success as guaranteed profitability.

## 27. Data Licensing

Before production, verify:
- IDX/BEI data rights
- redistribution rights
- historical data rights
- API limits
- commercial usage
- caching restrictions
- display/attribution requirements

Provider selection is an implementation decision and must be validated separately.

## 28. Open Decisions

Record decisions in `DECISION-LOG.md`:
1. production market-data provider
2. exact IDX universe
3. data licensing
4. charting library
5. authentication
6. deployment
7. notifications
8. AI provider/model
9. strategy formulas
10. scoring weights
11. transaction-cost assumptions
12. slippage model
13. execution timing

## 29. Global Engineering Rule

When feature completeness conflicts with data correctness, quantitative integrity, or risk safety:

**Choose correctness, quantitative integrity, and safety.**

A smaller correct trading assistant is preferable to a feature-rich system that produces misleading signals or biased backtests.
