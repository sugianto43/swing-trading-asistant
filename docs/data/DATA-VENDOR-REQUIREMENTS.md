# DATA-VENDOR-REQUIREMENTS.md

## IDX Swing Trading Assistant — Market Data Vendor Requirements

**Version:** 1.0  
**Status:** Phase 2 baseline  
**Market:** Indonesia Stock Exchange (IDX/BEI)

## 1. Purpose

Define the technical, quantitative, operational, and licensing requirements for selecting market-data vendors.

The application must remain vendor-agnostic:

```text
Vendor → Adapter → MarketDataProvider → Canonical Data → Domain
```

Vendor-specific API schemas must never leak into technical indicators, scanner, risk, backtesting, portfolio, or AI logic.

## 2. Required Data

### MVP / Tier 1
- IDX instrument master
- Daily OHLCV
- Historical daily OHLCV
- Trading calendar
- Corporate actions
- timestamps
- source metadata
- data-quality status

### Preferred / Tier 2
- intraday OHLCV
- latest quote
- market status
- sector/subsector
- index constituents
- suspended/delisted history

### Optional / Phase 9
- fundamentals
- earnings
- dividends
- announcements
- news
- ownership
- breadth
- flow data

## 3. Instrument Master

Required fields:

```text
instrument_id
symbol
company_name
exchange
MIC
currency
security_type
sector
subsector
listing_date
delisting_date
status
source
source_symbol
valid_from
valid_to
last_updated_at
```

Must support historical ticker changes, suspensions, and delistings.

## 4. Daily OHLCV

Minimum:

```text
instrument_id
timestamp
session_date
open
high
low
close
volume
source
ingested_at
```

Preferred:

```text
vwap
turnover
trades_count
adjusted_close
previous_close
change
change_percent
```

Validation:

```text
high >= max(open, close, low)
low <= min(open, close, high)
volume >= 0
```

## 5. Historical Data

Minimum target: 10 years of usable daily history where available. Preferred: 15+ years.

Coverage must be tested by representative IDX symbols rather than accepted from marketing claims.

Historical universe membership is strongly preferred for avoiding survivorship bias.

## 6. Corporate Actions

Required/preferred:
- splits
- reverse splits
- rights issues
- cash dividends
- stock dividends
- bonus issues
- ticker changes
- mergers/acquisitions where relevant
- suspension/relisting events

Raw and adjusted price series must be explicitly distinguished.

## 7. Trading Calendar

Required:
- trading dates
- holidays
- special sessions
- market open/close
- timezone

Canonical application timezone: `Asia/Jakarta`.

## 8. Intraday

Not required for the initial weekly-swing MVP.

If purchased, preferred:
`1m`, `5m`, `15m`, `30m`, `1h`.

Each bar must retain exchange timestamp, timezone, session identity, and source.

## 9. Latest Quote

Preferred:
- symbol
- timestamp
- price
- volume
- change
- change_percent
- bid/ask if available
- market_status
- source

Data state must distinguish:
`REALTIME`, `DELAYED`, `END_OF_DAY`, `STALE`, `UNKNOWN`.

## 10. Data Quality

Test:
- missing sessions
- missing fields
- invalid OHLC
- duplicates
- impossible prices
- negative volume
- timezone errors
- symbol inconsistencies
- corporate-action inconsistencies
- stale data
- historical revisions

## 11. Source Lineage

Every canonical record should be traceable to:

```text
provider
provider_symbol
provider_dataset
provider_timestamp
retrieved_at
raw_record_hash
data_version
```

Retain raw payloads where licensing permits.

## 12. API

Preferred:
- REST
- bulk historical download
- incremental updates
- pagination
- symbol lookup
- date ranges
- batch symbols
- rate-limit metadata
- clear errors

WebSocket is optional for MVP.

## 13. Reliability

The adapter must safely handle:
- timeout
- HTTP 429
- HTTP 5xx
- connection failure
- partial response
- provider outage
- schema changes

Ingestion must be idempotent.

## 14. Licensing

Before production, verify in writing:
- commercial use
- internal use
- display rights
- redistribution
- caching/storage
- historical retention
- derived-data rights
- number of users
- API-key restrictions
- attribution
- audit requirements

Public availability does not imply redistribution rights.

## 15. Security

- server-side API credentials
- secret manager/environment secrets
- key rotation
- no credentials in source control
- no credentials in browser
- sanitized logs

## 16. Cost

Evaluate total cost:

```text
subscription
+ API usage
+ historical data
+ realtime entitlement
+ display/non-display license
+ users
+ symbols
+ overage
+ exchange fees
```

## 17. Mock Provider

A mock provider is mandatory. Tests must not depend on internet access.

Fixtures must include:
- normal candles
- missing candles
- duplicates
- invalid OHLC
- corporate actions
- stale data
- symbol changes

## 18. Provider Contract

Example:

```python
class MarketDataProvider(Protocol):
    async def get_instruments(...): ...
    async def get_daily_bars(...): ...
    async def get_intraday_bars(...): ...
    async def get_latest_quote(...): ...
    async def get_corporate_actions(...): ...
    async def get_calendar(...): ...
```

Exact interface is a Phase 2 TDD decision.

## 19. Acceptance Tests

Test representative:
- large caps
- mid caps
- small caps
- recently listed stocks
- suspended stocks
- delisted examples where available

Validate:
- coverage
- OHLC
- duplicates
- missing sessions
- timestamps
- corporate actions
- historical depth
- retries
- rate limits
- outage behavior
- licensing

## 20. Phase Mapping

Phase 1: mock/fixture data only.

Phase 2: vendor POC, selection, adapter, canonical model.

Phase 3: technical engine consumes canonical data only.

Phase 4: scanner consumes domain data only.

Phase 5: validated historical datasets with source/version metadata.

Phase 9: evaluate additional intelligence vendors.

## 21. Production Go-Live Gate

```text
[ ] IDX coverage verified
[ ] Historical coverage verified
[ ] OHLCV quality verified
[ ] Corporate actions verified
[ ] Calendar verified
[ ] Timestamp semantics verified
[ ] Licensing approved
[ ] API limits documented
[ ] Cost approved
[ ] Reliability tested
[ ] Adapter tests pass
[ ] Backtest data quality reviewed
[ ] Fallback strategy documented
```

## 22. Hard Rule

Do not build the trading domain around a vendor API schema. The vendor is replaceable; the canonical data contract is part of the product.
