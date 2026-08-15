import uuid
from datetime import UTC, date, datetime

from app.db.enums import DataQualityStatus
from app.db.models import PriceBar
from app.marketdata.dedupe import dedupe_price_bars_by_trade_date


def _bar(trade_date: date, close: float, source: str, ingested_at: datetime) -> PriceBar:
    return PriceBar(
        instrument_id=uuid.uuid4(),
        trade_date=trade_date,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1000,
        source=source,
        source_symbol="BBCA.JK",
        quality_status=DataQualityStatus.VALID,
        ingested_at=ingested_at,
    )


def test_dedupe_keeps_most_recently_ingested_bar_for_duplicate_date() -> None:
    same_date = date(2024, 1, 5)
    older = _bar(same_date, 100.0, "fixture", datetime(2024, 1, 5, 8, tzinfo=UTC))
    newer = _bar(same_date, 200.0, "yfinance", datetime(2024, 1, 5, 20, tzinfo=UTC))

    result = dedupe_price_bars_by_trade_date([older, newer])

    assert len(result) == 1
    assert result[0].close == 200.0


def test_dedupe_no_duplicates_returns_all_bars_unchanged() -> None:
    bars = [
        _bar(date(2024, 1, 2), 100.0, "fixture", datetime(2024, 1, 2, tzinfo=UTC)),
        _bar(date(2024, 1, 3), 101.0, "fixture", datetime(2024, 1, 3, tzinfo=UTC)),
    ]
    result = dedupe_price_bars_by_trade_date(bars)
    assert len(result) == 2
