# Phase 16 — Technical Design Document

## Architecture
A chat-style interface calling `POST /ai/analyze` (question, optional symbol) and a snapshot history view (`GET /ai/snapshots`). Each response renders the model's text alongside its `guardrail_flags` (never hidden — a flagged response is still shown, with the flag visible, per AI-GUARDRAILS.md's "flags recorded for human review, never silently dropped") and, where useful, the structured tool-call data that grounded the answer (so a `DATA_UNAVAILABLE` result is visibly a gap, not silently absorbed into prose).

## Required Interfaces
API client methods for `/ai/analyze` and `/ai/snapshots`. No client-side provider selection or API-key handling — the backend owns provider configuration (`GEMINI_API_KEY`), consistent with ADR-0003; the UI only ever sees a 503 if no provider is configured, and must render that plainly, not as a generic error.

## Data
None new. No conversation state is invented client-side beyond what `AnalysisSnapshot` already persists — the chat UI is a view over that history, not a separate client-only session store pretending to be more than it is.

## Tests
Chat interaction tests (question submit, tool-call/guardrail-flag rendering, DATA_UNAVAILABLE rendering, 503-no-provider rendering), snapshot history render tests, API client tests.
