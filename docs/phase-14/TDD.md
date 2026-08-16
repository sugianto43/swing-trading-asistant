# Phase 14 — Technical Design Document

## Architecture
A trade-plan builder form (`POST /risk/trade-plans` — symbol, setup type, plan date, capital, existing positions) and a trade-plan list/detail view (`GET /risk/trade-plans`, `/risk/trade-plans/{id}`), reachable from Phase 13's scanner candidate rows ("build a plan for this setup").

## Required Interfaces
API client methods for the trade-plan endpoints. The rejection-reasons array on a `REJECTED` plan must be rendered verbatim — the UI must not interpret, summarize, or hide any reason the backend returned.

## Data
None new. Capital input is user-supplied per request (mirrors the backend's own `capital` parameter — no client-side default that could be mistaken for a real portfolio value).

## Tests
Form validation tests (client-side bounds mirroring the backend's own, e.g. positive capital), success/rejected/error-response rendering tests, API client tests.
