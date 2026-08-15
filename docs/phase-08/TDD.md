# Phase 8 — Technical Design Document

## Architecture
LLM orchestrator → typed domain tools → structured analysis → persisted snapshot.

## Tools
Stock snapshot, technicals, setup, plan, backtest, positions, journal, market regime, portfolio risk.

## Guardrails
No arbitrary SQL, no execution, no invented numerical facts, no risk-limit changes.

## Tests
Prompt injection, unsupported data, fake price requests, unauthorized actions, numerical grounding.
