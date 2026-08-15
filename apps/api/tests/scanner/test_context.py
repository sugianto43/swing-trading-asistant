import uuid
from datetime import UTC, date, datetime

from app.db.enums import DataQualityStatus
from app.db.models import IndicatorSnapshot, PriceBar
from app.scanner.context import build_scan_points


def _bar(instrument_id, trade_date: date, close: float, ingested_at=None) -> PriceBar:
    return PriceBar(
        instrument_id=instrument_id,
        trade_date=trade_date,
        open=close,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=1000,
        source="fixture",
        source_symbol="BBCA.JK",
        quality_status=DataQualityStatus.VALID,
        ingested_at=ingested_at or datetime(2024, 1, 1, tzinfo=UTC),
    )


def _snapshot(instrument_id, trade_date: date, **kwargs) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        instrument_id=instrument_id, trade_date=trade_date, indicator_version="v1", **kwargs
    )


def test_build_scan_points_joins_bars_with_snapshots() -> None:
    iid = uuid.uuid4()
    bars = [_bar(iid, date(2024, 1, 2), 100.0), _bar(iid, date(2024, 1, 3), 101.0)]
    snapshots = [
        _snapshot(iid, date(2024, 1, 2), sma_20=99.0),
        _snapshot(iid, date(2024, 1, 3), sma_20=100.0),
    ]

    points = build_scan_points(bars, [], snapshots)

    assert len(points) == 2
    assert points[0].trade_date == date(2024, 1, 2)
    assert points[0].sma_20 == 99.0
    assert points[1].close == 101.0


def test_build_scan_points_drops_dates_without_indicator_snapshot() -> None:
    iid = uuid.uuid4()
    bars = [_bar(iid, date(2024, 1, 2), 100.0), _bar(iid, date(2024, 1, 3), 101.0)]
    snapshots = [_snapshot(iid, date(2024, 1, 2), sma_20=99.0)]  # no snapshot for Jan 3

    points = build_scan_points(bars, [], snapshots)

    assert len(points) == 1
    assert points[0].trade_date == date(2024, 1, 2)


def test_build_scan_points_empty_input() -> None:
    assert build_scan_points([], [], []) == []


def test_build_scan_points_dedupes_multi_source_bars() -> None:
    iid = uuid.uuid4()
    same_date = date(2024, 1, 2)
    older = _bar(iid, same_date, 100.0, ingested_at=datetime(2024, 1, 2, 8, tzinfo=UTC))
    newer = _bar(iid, same_date, 200.0, ingested_at=datetime(2024, 1, 2, 20, tzinfo=UTC))
    snapshots = [_snapshot(iid, same_date, sma_20=150.0)]

    points = build_scan_points([older, newer], [], snapshots)

    assert len(points) == 1
    assert points[0].close == 200.0
