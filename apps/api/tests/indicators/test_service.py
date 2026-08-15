from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.db.enums import CorporateActionType, DataQualityStatus, ListingStatus
from app.db.models import CorporateAction, IndicatorSnapshot, Instrument, PriceBar
from app.indicators.service import IndicatorService
from app.indicators.versioning import INDICATOR_VERSION


def _seed_instrument(db_session, symbol: str = "BBCA") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Bank Central Asia Tbk",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_bars(db_session, instrument: Instrument, n: int = 30) -> None:
    for i in range(n):
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.0 + i,
                volume=1000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
    db_session.commit()


def test_compute_and_persist_requires_seeded_instrument(db_session) -> None:
    service = IndicatorService(db_session)
    with pytest.raises(ValueError, match="not seeded"):
        service.compute_and_persist("BBCA", date(2024, 1, 1), date(2024, 1, 31))


def test_compute_and_persist_writes_rows(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_bars(db_session, instrument, n=30)

    summary = service_compute(db_session, "BBCA", date(2024, 1, 1), date(2024, 1, 30))

    assert summary.computed == 30
    assert summary.persisted == 30
    persisted = db_session.scalars(select(IndicatorSnapshot)).all()
    assert len(persisted) == 30
    assert all(row.indicator_version == INDICATOR_VERSION for row in persisted)


def test_compute_and_persist_is_idempotent(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_bars(db_session, instrument, n=30)

    service_compute(db_session, "BBCA", date(2024, 1, 1), date(2024, 1, 30))
    service_compute(db_session, "BBCA", date(2024, 1, 1), date(2024, 1, 30))

    persisted = db_session.scalars(select(IndicatorSnapshot)).all()
    assert len(persisted) == 30


def test_compute_and_persist_only_persists_rows_in_range(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_bars(db_session, instrument, n=60)

    # request only the second half, but the full 60-day history is still
    # used internally for correct warm-up
    summary = service_compute(
        db_session,
        "BBCA",
        date(2024, 1, 1) + timedelta(days=30),
        date(2024, 1, 1) + timedelta(days=59),
    )

    assert summary.computed == 60
    assert summary.persisted == 30
    persisted = db_session.scalars(select(IndicatorSnapshot)).all()
    assert len(persisted) == 30


def test_compute_and_persist_warm_up_uses_full_history_before_range(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_bars(db_session, instrument, n=60)

    # SMA20 needs 20 bars of warm-up; asking for a range starting at day 30
    # should still get a populated sma_20 since 30 days of history exist
    # before it.
    service_compute(
        db_session,
        "BBCA",
        date(2024, 1, 1) + timedelta(days=30),
        date(2024, 1, 1) + timedelta(days=30),
    )
    row = db_session.scalar(select(IndicatorSnapshot))
    assert row.sma_20 is not None


def test_compute_and_persist_zero_bars_returns_empty_summary(db_session) -> None:
    _seed_instrument(db_session)  # instrument exists but no PriceBar rows

    summary = service_compute(db_session, "BBCA", date(2024, 1, 1), date(2024, 1, 31))

    assert summary.computed == 0
    assert summary.persisted == 0
    assert db_session.scalars(select(IndicatorSnapshot)).all() == []


def test_compute_and_persist_start_after_end_persists_nothing(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_bars(db_session, instrument, n=30)

    summary = service_compute(db_session, "BBCA", date(2024, 6, 1), date(2024, 1, 1))

    assert summary.persisted == 0
    assert db_session.scalars(select(IndicatorSnapshot)).all() == []


def test_compute_and_persist_is_value_reproducible_not_just_row_count(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_bars(db_session, instrument, n=30)

    service_compute(db_session, "BBCA", date(2024, 1, 1), date(2024, 1, 30))
    first_run = {
        row.trade_date: (row.sma_20, row.rsi_14, row.macd)
        for row in db_session.scalars(select(IndicatorSnapshot)).all()
    }

    service_compute(db_session, "BBCA", date(2024, 1, 1), date(2024, 1, 30))
    second_run = {
        row.trade_date: (row.sma_20, row.rsi_14, row.macd)
        for row in db_session.scalars(select(IndicatorSnapshot)).all()
    }

    assert first_run == second_run


def test_compute_and_persist_ignores_split_ingested_after_persist_to(db_session) -> None:
    # A historical snapshot computed "as of" a past date must not be
    # retroactively adjusted by a split that, as of that date, had not
    # happened yet (MASTER-PRD §8: only information available at or
    # before T). The split below is dated well after persist_to.
    instrument = _seed_instrument(db_session)
    for i in range(10):
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=date(2024, 1, 1) + timedelta(days=i),
                open=2000.0,
                high=2000.0,
                low=2000.0,
                close=2000.0,
                volume=1000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=date(2024, 6, 1),  # well after persist_to below
            source="fixture",
            source_symbol=instrument.source_symbol,
            ratio=2.0,
        )
    )
    db_session.commit()

    service_compute(db_session, "BBCA", date(2024, 1, 1), date(2024, 1, 10))

    rows = db_session.scalars(
        select(IndicatorSnapshot).order_by(IndicatorSnapshot.trade_date)
    ).all()
    # the underlying series is flat (every bar close=2000); if the
    # not-yet-happened split were wrongly applied, return_1d would show a
    # spurious jump at whatever point the (buggy) adjustment logic kicked
    # in. A correctly-unadjusted flat series has zero return every day.
    assert all(float(row.return_1d) == 0.0 for row in rows if row.return_1d is not None)


def service_compute(db_session, symbol, start, end):
    return IndicatorService(db_session).compute_and_persist(symbol, start, end)
