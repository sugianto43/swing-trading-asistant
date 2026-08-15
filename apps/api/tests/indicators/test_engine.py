import uuid
from datetime import UTC, date, datetime, timedelta

from app.db.enums import CorporateActionType, DataQualityStatus
from app.db.models import CorporateAction, PriceBar
from app.indicators.engine import _dedupe_by_trade_date, compute_indicator_snapshot
from app.indicators.versioning import INDICATOR_VERSION


def _bar(
    trade_date: date,
    close: float,
    quality: DataQualityStatus = DataQualityStatus.VALID,
    source: str = "fixture",
    ingested_at: datetime | None = None,
):
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
        quality_status=quality,
        ingested_at=ingested_at,
    )


def _series(n: int, start_price: float = 100.0, start_date: date = date(2024, 1, 1)):
    return [_bar(start_date + timedelta(days=i), start_price + i) for i in range(n)]


def test_compute_indicator_snapshot_empty_input() -> None:
    assert compute_indicator_snapshot([], []) == []


def test_compute_indicator_snapshot_length_and_order_match_input() -> None:
    bars = _series(30)
    rows = compute_indicator_snapshot(bars, [])
    assert len(rows) == 30
    assert [r.trade_date for r in rows] == [b.trade_date for b in bars]


def test_compute_indicator_snapshot_tags_indicator_version() -> None:
    rows = compute_indicator_snapshot(_series(5), [])
    assert all(r.indicator_version == INDICATOR_VERSION for r in rows)


def test_compute_indicator_snapshot_excludes_invalid_bars() -> None:
    bars = _series(25)
    # corrupt one bar in the middle as INVALID
    bars[10] = _bar(bars[10].trade_date, -999, quality=DataQualityStatus.INVALID)

    rows = compute_indicator_snapshot(bars, [])

    # the INVALID bar's date must not appear in the output sequence at all
    assert bars[10].trade_date not in [r.trade_date for r in rows]
    assert len(rows) == 24


def test_compute_indicator_snapshot_includes_stale_bars() -> None:
    # STALE is a valid DataQualityStatus but nothing in the codebase
    # currently assigns it to a PriceBar (Phase 2's is_stale() only reports
    # via notes) — this pins the contract for if/when it ever is: only
    # INVALID is excluded, everything else (including STALE) is included.
    bars = _series(25)
    bars[10] = _bar(bars[10].trade_date, bars[10].close, quality=DataQualityStatus.STALE)

    rows = compute_indicator_snapshot(bars, [])

    assert bars[10].trade_date in [r.trade_date for r in rows]
    assert len(rows) == 25


def test_compute_indicator_snapshot_handles_missing_day_gap() -> None:
    # a real gap: no bar exists at all for this date (not flagged invalid,
    # just absent from the input, e.g. a weekend/holiday or an
    # unobserved session) — the engine must not crash and must not
    # fabricate a phantom entry for the missing date.
    bars = _series(30)
    missing_date = bars[15].trade_date
    bars_with_gap = bars[:15] + bars[16:]

    rows = compute_indicator_snapshot(bars_with_gap, [])

    assert len(rows) == 29
    assert missing_date not in [r.trade_date for r in rows]
    # SMA20 should still populate using the 20 most-recent *available* bars
    assert rows[-1].sma_20 is not None


def test_dedupe_by_trade_date_keeps_most_recently_ingested() -> None:
    same_date = date(2024, 1, 5)
    older = _bar(
        same_date, 100.0, source="fixture", ingested_at=datetime(2024, 1, 5, 8, tzinfo=UTC)
    )
    newer = _bar(
        same_date,
        200.0,
        source="yfinance",
        ingested_at=datetime(2024, 1, 5, 20, tzinfo=UTC),
    )

    result = _dedupe_by_trade_date([older, newer])

    assert len(result) == 1
    assert result[0].close == 200.0


def test_compute_indicator_snapshot_dedupes_multi_source_same_date() -> None:
    # Phase 2's unique constraint is (instrument_id, trade_date, source),
    # not (instrument_id, trade_date) — two bars for the same date can
    # legitimately coexist if ingested from different providers. Without
    # dedup this corrupts every rolling-window value, not just this date.
    bars = _series(25)
    duplicate_date = bars[12].trade_date
    fixture_bar = _bar(
        duplicate_date,
        bars[12].close,
        source="fixture",
        ingested_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    yfinance_bar = _bar(
        duplicate_date,
        bars[12].close,
        source="yfinance",
        ingested_at=datetime(2024, 1, 2, tzinfo=UTC),
    )
    bars_with_duplicate = [*bars[:12], fixture_bar, yfinance_bar, *bars[13:]]

    rows = compute_indicator_snapshot(bars_with_duplicate, [])

    # exactly one row for the duplicated date, not two, and no crash
    matching_dates = [r.trade_date for r in rows if r.trade_date == duplicate_date]
    assert len(matching_dates) == 1
    assert len(rows) == 25


def test_compute_indicator_snapshot_includes_suspect_bars() -> None:
    bars = _series(25)
    bars[10] = _bar(bars[10].trade_date, bars[10].close, quality=DataQualityStatus.SUSPECT)

    rows = compute_indicator_snapshot(bars, [])

    assert bars[10].trade_date in [r.trade_date for r in rows]
    assert len(rows) == 25


def test_compute_indicator_snapshot_is_deterministic() -> None:
    bars = _series(60)
    first = compute_indicator_snapshot(bars, [])
    second = compute_indicator_snapshot(bars, [])
    assert first == second


def test_compute_indicator_snapshot_reorders_out_of_order_input() -> None:
    bars = _series(10)
    shuffled = [bars[3], bars[0], bars[5], bars[1], bars[2], bars[4], *bars[6:]]
    rows = compute_indicator_snapshot(shuffled, [])
    assert [r.trade_date for r in rows] == sorted(b.trade_date for b in bars)


def test_compute_indicator_snapshot_no_look_ahead_future_mutation() -> None:
    """The core adversarial test required by Phase 3 TDD: indicator values
    for indices before a mutation point must be byte-identical regardless
    of what happens to bars after that point."""
    bars = _series(40)

    baseline = compute_indicator_snapshot(bars[:20], [])

    mutated = list(bars)
    for i in range(20, 40):
        # corrupt every "future" bar relative to the baseline's cutoff
        mutated[i] = _bar(bars[i].trade_date, 999999.0)
    extended = compute_indicator_snapshot(mutated, [])

    assert extended[:20] == baseline


def test_compute_indicator_snapshot_applies_split_adjustment() -> None:
    instrument_id = uuid.uuid4()
    bars = [
        PriceBar(
            instrument_id=instrument_id,
            trade_date=date(2024, 1, 1) + timedelta(days=i),
            open=2000.0,
            high=2000.0,
            low=2000.0,
            close=2000.0,
            volume=1000,
            source="fixture",
            source_symbol="BBCA.JK",
            quality_status=DataQualityStatus.VALID,
        )
        for i in range(5)
    ] + [
        PriceBar(
            instrument_id=instrument_id,
            trade_date=date(2024, 1, 10) + timedelta(days=i),
            open=1000.0,
            high=1000.0,
            low=1000.0,
            close=1000.0,
            volume=1000,
            source="fixture",
            source_symbol="BBCA.JK",
            quality_status=DataQualityStatus.VALID,
        )
        for i in range(5)
    ]
    split = CorporateAction(
        instrument_id=instrument_id,
        action_type=CorporateActionType.SPLIT,
        ex_date=date(2024, 1, 8),
        source="fixture",
        source_symbol="BBCA.JK",
        ratio=2.0,
    )

    rows = compute_indicator_snapshot(bars, [split])

    # without adjustment this would look like a 50% price crash; with
    # adjustment applied the whole series is a flat 1000 line
    sma_values = [r.sma_20 for r in rows if r.sma_20 is not None]
    assert sma_values == [] or all(v == 1000.0 for v in sma_values)
    # returns should show no artificial jump across the split boundary
    boundary_row = next(r for r in rows if r.trade_date == date(2024, 1, 10))
    assert boundary_row.return_1d == 0.0
