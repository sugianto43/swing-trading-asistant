# Phase 3 — Technical Design Document

## Architecture
Canonical price bars → indicator engine → indicator snapshots.

## Indicators
SMA20/50/200, EMA20/50, RSI14, ATR14, MACD, Bollinger Bands, volume SMA, relative volume, rolling high/low, returns, volatility.

## Rules
Explicit warm-up values; no future data; deterministic output; one canonical calculation per indicator.

## Tests
Known-value tests, insufficient data, missing data, timestamp alignment, and adversarial future-candle mutation tests.
