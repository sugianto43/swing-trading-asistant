# Phase 4 — Technical Design Document

## Architecture
Scanner orchestrates setup detectors and scoring; it consumes Phase 3 outputs and does not reimplement indicators.

## Setups
Breakout, pullback, momentum continuation, MA reclaim, volatility contraction → expansion.

## Scoring
Configurable weighted components with persisted/explainable breakdown.

## Candidate
Symbol, setup, score, components, qualifying/disqualifying conditions, data status, invalidation conditions.

## Tests
Positive/negative/boundary/stale-data/future-data cases for every setup and deterministic ranking.
