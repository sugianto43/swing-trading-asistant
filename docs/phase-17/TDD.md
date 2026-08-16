# Phase 17 — Technical Design Document

## Architecture
Alerts list (`GET /alerts`, filters: `alert_type`, `symbol`, `trigger_date`) plus a live subscription to Phase 10's SSE endpoint (`GET /alerts/stream`) via the browser's native `EventSource`, merging newly-pushed alerts into the list view as they arrive.

## Required Interfaces
API client method for `GET /alerts`; an `EventSource`-based hook/utility for the stream, with explicit reconnect-on-drop handling (the backend keeps the connection alive with `: keep-alive` comments per Phase 10's `SSE_STREAM_TIMEOUT_SECONDS` — the client must tolerate those, not treat them as errors).

## Data
None new. The client renders exactly what the backend's deduplicated `alerts` table produced — no client-side re-deduplication logic that could diverge from the backend's own `uq_alert_identity` constraint as the source of truth.

## Tests
List render tests (filters, empty/populated states), SSE hook tests (message received, keep-alive tolerated, reconnect on drop — using a mocked `EventSource`), API client tests.
