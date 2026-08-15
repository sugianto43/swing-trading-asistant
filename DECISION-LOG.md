# Architecture Decision Log

Use this file for decisions that affect multiple phases.

## ADR-0001 — Decision Log
Status: Accepted

Record each decision using:

### ADR-NNNN — Title
Date:
Status:
Context:
Decision:
Alternatives:
Consequences:
Affected phases:

## ADR-0002 — Phase 2 Market Data Vendor: yfinance (Personal-Use POC)
Date: 2026-08-15
Status: Accepted (personal-use scope only; not a production licensing decision)
Context: docs/data/DATA-VENDOR-REQUIREMENTS.md and VENDOR-EVALUATION.md establish a vendor-agnostic
`MarketDataProvider` contract and recommend a Stage 1 prototype using a mock provider plus one
developer-friendly candidate. This application is for personal, non-commercial, single-user use.
No licensed IDX data contract has been evaluated or purchased; the VENDOR-EVALUATION.md matrix
remains entirely "TBD".
Decision: Implement `FixtureProvider` (mandatory mock, used for all automated tests — no
internet dependency) and `YfinanceProvider` (adapter over the unofficial `yfinance` package) as
the two Phase 2 provider implementations, both satisfying the same `MarketDataProvider` protocol.
yfinance was chosen over other free options (e.g. scraping IDX directly) because it has broad
existing IDX (`.JK`) coverage and a stable-enough Python interface for a hobby project.
Alternatives: Twelve Data free tier (official API, more restrictive rate limits, IDX coverage
unverified); a licensed local IDX redistributor (Antara/IMQ, IQ Plus Prima, RTI Infokom) — not
pursued, since that requires a paid commercial contract this project does not have.
Consequences:
- Not a licensed/production data source. Unofficial, reverse-engineered access; Yahoo's terms do
  not sanction this kind of programmatic use. Acceptable only because usage is personal,
  non-commercial, and not redistributed. Must be revisited before any commercial/multi-user use.
- yfinance has no IDX instrument-master API → the instrument universe is bootstrapped from a
  static local seed (`app/marketdata/seed/idx_instruments.csv`), not vendor data.
- yfinance has no trading-calendar API → `trading_calendar` is populated incrementally from
  observed trading days in ingested bars, not a pre-known holiday schedule.
- Corporate actions are limited to what `yfinance`'s `.actions` exposes (dividends, splits) — no
  rights issues, ticker changes, or suspension/relisting events.
- The provider abstraction means swapping to a licensed vendor later requires only a new adapter
  class, not domain/schema changes (per the "vendor can change, canonical contract can't" rule in
  VENDOR-EVALUATION.md §12).
Affected phases: 2 (built), 3+ (consume canonical data only, per the same rule), any future
production go-live (must re-run the full vendor evaluation and licensing gate first).
