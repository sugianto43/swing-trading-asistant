# Phase 6 — Technical Design Document

## Architecture
Setup/trade inputs → deterministic risk engine → trade plan.

## Outputs
Entry zone, stop, targets, size, capital, max loss, R:R, exposure, risk flags.

## Rules
Configurable risk limits; AI cannot modify them; invalid plans must fail validation.

## Tests
Invalid stop, negative R:R, insufficient capital, minimum lot, concentration, fees/slippage.
