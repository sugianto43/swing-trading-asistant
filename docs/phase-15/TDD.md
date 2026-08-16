# Phase 15 — Technical Design Document

## Architecture
Execution recording form (`POST /executions` — symbol, side, quantity, price, fee, executed_at, optional trade_plan_id), open positions list (`GET /positions`, `/positions/{id}`), journal entry form (`POST /positions/{id}/journal`), and performance dashboards (`GET /performance/summary`, `/by-setup`, `/by-sector`, `/by-holding-period`, `/by-score-bucket`, `/behavior`).

## Required Interfaces
API client methods for the above. The execution form must surface the backend's own validation errors (e.g. overselling → 409) directly — no client-side "auto-correction" of a rejected execution.

## Data
None new. This phase is the UI's closest approach to "acting" in the system, and per AI-GUARDRAILS.md/MASTER-PRD's no-automated-trading rule, every execution recorded here is the human confirming a trade they already made elsewhere — the UI never calls a broker or any execution venue.

## Tests
Form validation and error-rendering tests (overselling, invalid quantity/price), position/journal/performance render tests across empty/populated states, API client tests.
