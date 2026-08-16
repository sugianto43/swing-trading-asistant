# Phase 13 — Technical Design Document

## Architecture
Two screens on top of Phase 12's shell: Market Overview (`GET /intelligence/breadth`, `/intelligence/sector-performance`) and Scanner/Top Swing Candidates (`GET /scanner/candidates` with the filters/sort MASTER-PRD §15 specifies: universe, sector, liquidity, price, setup, minimum score, trend, volume, volatility, market regime; sort by score/liquidity/momentum/risk-reward/relative volume). An instrument detail view (`GET /instruments/{symbol}`, `/instruments/{symbol}/indicators`, `/instruments/{symbol}/candidates`) with an indicator chart.

## Required Interfaces
API client methods for the above endpoints (extending Phase 12's client). A charting library decision is explicitly deferred to `/plan-phase 13` (candidates: `lightweight-charts`, `recharts` — evaluate against MASTER-PRD §18's "charting library" suggestion, bundle size, and whether OHLC/indicator overlay is needed).

## Data
None new — read-only against existing backend data. Stale/missing data (Phase 2's `is_stale`) must render as an explicit state, never a silently empty or fabricated chart.

## Tests
Component tests per screen (loading/empty/error/populated states), API client tests, filter/sort interaction tests.
