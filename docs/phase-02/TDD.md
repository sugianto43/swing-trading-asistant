# Phase 2 — Technical Design Document

## Architecture
Provider interface → ingestion service → validation → canonical persistence.

## Core Models
Instrument, PriceBar, CorporateAction, TradingCalendar.

## Requirements
Source lineage, timestamps, freshness, quality status, explicit timezone policy, duplicate handling.

## Provider
MarketDataProvider with quotes, historical prices, corporate actions, fundamentals, calendar.

## Tests
Provider contract, OHLC validation, duplicates, missing sessions, timestamps, reproducibility.
