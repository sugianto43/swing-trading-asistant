"""Seeds real, deterministic data for the golden-journey E2E spec
(Phase 18). Copied into the running `api` container and executed there
by seed.sh — kept out of apps/api itself since this is frontend-owned
test tooling, not backend application code (git diff --stat -- apps/api
must stay empty for this phase).

Produces: a seeded BBCA instrument with 220 days of price history ending
in a decisive breakout on the final day (clears the previous session's
own bar without a same-day post-close jump), high relative volume, and
one real persisted BREAKOUT scan candidate on PLAN_DATE — the same
pattern manually re-derived by hand during every phase's sign-off this
session, now written once and reused.
"""

import random
from datetime import date, timedelta

from app.indicators.service import IndicatorService
from app.db.session import SessionLocal
from app.marketdata.fixture_provider import FixtureProvider
from app.marketdata.ingestion import IngestionService
from app.marketdata.provider import RawBar
from app.scanner.service import ScannerService

SYMBOL = "BBCA"
SOURCE_SYMBOL = "BBCA.JK"
PLAN_DATE = date(2024, 3, 1)
LOOKBACK_DAYS = 220

random.seed(42)


def _trading_days(end: date, days: int) -> list[date]:
    out: list[date] = []
    d = end - timedelta(days=days)
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def build_bars() -> list[RawBar]:
    trading_days = _trading_days(PLAN_DATE, LOOKBACK_DAYS)
    n = len(trading_days)
    bars: list[RawBar] = []
    price = 900.0
    for i, trade_date in enumerate(trading_days):
        is_last = i == n - 1
        if is_last:
            price *= 1.08  # decisive breakout above the prior 20-day range
        elif i < n - 30:
            price *= 1 + random.uniform(-0.006, 0.006)
        else:
            price *= 1 + random.uniform(-0.004, 0.004)  # tight range-bound tail
        open_ = price * (1 + random.uniform(-0.003, 0.003))
        high = max(open_, price) * (1 + random.uniform(0.001, 0.01))
        low = min(open_, price) * (1 - random.uniform(0.001, 0.01))
        volume = int(5_000_000 * (2.5 if is_last else 1.0) * random.uniform(0.9, 1.1))
        bars.append(
            RawBar(
                source_symbol=SOURCE_SYMBOL,
                trade_date=trade_date,
                open=round(open_, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(price, 2),
                volume=volume,
                source="fixture",
            )
        )
    return bars


def main() -> None:
    bars = build_bars()
    provider = FixtureProvider(bars={SOURCE_SYMBOL: bars})
    session = SessionLocal()
    try:
        ingestion = IngestionService(session, provider)
        print("instruments:", ingestion.sync_instruments())
        summary = ingestion.ingest_prices(SYMBOL, bars[0].trade_date, bars[-1].trade_date)
        print("prices:", summary.status.value, summary.records_processed, summary.notes)

        indicators = IndicatorService(session)
        idx_summary = indicators.compute_and_persist(SYMBOL, bars[0].trade_date, bars[-1].trade_date)
        print("indicators:", idx_summary)

        scanner = ScannerService(session)
        result = scanner.scan_symbol(SYMBOL, as_of=PLAN_DATE)
        print("scan:", result)

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
