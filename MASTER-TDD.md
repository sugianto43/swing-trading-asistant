# IDX Swing Trading Assistant — Master TDD

## Purpose
Technical implementation baseline for the IDX Swing Trading Assistant.

## Architecture
- Web: Next.js + React + TypeScript
- API: FastAPI + Python
- Database: PostgreSQL
- Cache/queue: Redis
- Workers: Python
- Analytics: Pandas/NumPy
- Optional backtesting framework: Backtrader behind an internal strategy abstraction
- AI: provider-agnostic LLM tool-calling layer
- Deployment: Docker + managed infrastructure

## Core Boundaries
Market data → validation → technical engine → scanner → intelligence → risk → trade plan → AI → manual execution → position → journal → performance.

## Canonical Sources
- Market facts: market-data services
- Indicators: technical engine
- Risk: risk engine
- Backtest metrics: backtest engine
- AI: explanation/orchestration only

## Global Non-Functional Requirements
- deterministic quantitative calculations
- UTC storage with explicit market-local timezone conversion
- migrations for schema changes
- typed APIs
- structured logging
- testability
- no automated order execution
- provider abstraction
- data lineage
- stale-data detection
- no look-ahead bias

## Repository Convention
Prefer:
apps/web
apps/api
workers
packages/shared
infra
docs
tests

Adapt to the actual repository if it already has a better established structure.
