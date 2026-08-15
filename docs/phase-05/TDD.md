# Phase 5 — Technical Design Document

## Architecture
Dataset/version → strategy → execution simulator → portfolio ledger → metrics.

## Requirements
No look-ahead, explicit execution timing, fees, slippage, position sizing, corporate-action treatment, train/test and walk-forward validation.

## Reproducibility
Pin dataset, strategy version, parameters, execution and cost model.

## Tests
Adversarial future leakage, cost calculations, equity curve, drawdown, trade ledger, reproducibility.
