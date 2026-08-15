# Phase 9 — Technical Design Document

## Architecture
Event/news/fundamental ingestion → normalization → entity matching → classification → intelligence API.

## Events
Earnings, dividends, splits, rights, buybacks, M&A, halts, regulatory and macro events.

## Critical Rule
Historical analysis uses information only from its public availability timestamp.

## Tests
Event deduplication, timestamps, availability leakage, sector/breadth calculations, event-study windows.
