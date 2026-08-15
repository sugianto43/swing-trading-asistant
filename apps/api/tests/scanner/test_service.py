from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.db.enums import CorporateActionType, DataQualityStatus, ListingStatus, ScanStatus
from app.db.models import (
    CorporateAction,
    IndicatorSnapshot,
    Instrument,
    PriceBar,
    ScanCandidate,
    ScanRun,
)
from app.scanner.context import build_scan_points
from app.scanner.service import ScannerService

AS_OF = date(2024, 6, 1)


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


def _seed_momentum_qualifying_data(db_session, instrument: Instrument, trade_date: date) -> None:
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=110.0,
            high=111.0,
            low=109.0,
            close=110.0,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id,
            trade_date=trade_date,
            indicator_version="v1",
            sma_50=100.0,
            sma_200=90.0,
            rsi_14=60.0,
            macd_histogram=0.5,
        )
    )
    db_session.commit()


def test_scan_symbol_requires_seeded_instrument(db_session) -> None:
    service = ScannerService(db_session)
    with pytest.raises(ValueError, match="not seeded"):
        service.scan_symbol("BBCA", AS_OF)


def test_scan_symbol_persists_qualifying_candidate(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_momentum_qualifying_data(db_session, instrument, AS_OF)

    result = ScannerService(db_session).scan_symbol("BBCA", AS_OF)

    assert result.skipped_stale is False
    assert result.candidates_persisted >= 1
    persisted = db_session.scalars(select(ScanCandidate)).all()
    assert len(persisted) >= 1
    assert all(c.instrument_id == instrument.id for c in persisted)


def test_scan_symbol_is_idempotent(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_momentum_qualifying_data(db_session, instrument, AS_OF)
    service = ScannerService(db_session)

    service.scan_symbol("BBCA", AS_OF)
    count_after_first = len(db_session.scalars(select(ScanCandidate)).all())
    service.scan_symbol("BBCA", AS_OF)
    count_after_second = len(db_session.scalars(select(ScanCandidate)).all())

    assert count_after_first == count_after_second


def test_scan_symbol_skips_stale_data_and_persists_nothing(db_session) -> None:
    instrument = _seed_instrument(db_session)
    stale_date = AS_OF - timedelta(days=30)  # well past the default staleness threshold
    _seed_momentum_qualifying_data(db_session, instrument, stale_date)

    result = ScannerService(db_session).scan_symbol("BBCA", AS_OF)

    assert result.skipped_stale is True
    assert result.candidates_persisted == 0
    assert db_session.scalars(select(ScanCandidate)).all() == []


def test_scan_symbol_boundary_exactly_at_staleness_threshold_is_fresh(db_session) -> None:
    instrument = _seed_instrument(db_session)
    # DEFAULT_MAX_STALENESS_DAYS is 5; a gap of exactly 5 days is still
    # fresh (the check is "> max_staleness_days", not ">=").
    boundary_date = AS_OF - timedelta(days=5)
    _seed_momentum_qualifying_data(db_session, instrument, boundary_date)

    result = ScannerService(db_session).scan_symbol("BBCA", AS_OF)

    assert result.skipped_stale is False


def test_scan_symbol_boundary_one_day_past_staleness_threshold_is_stale(db_session) -> None:
    instrument = _seed_instrument(db_session)
    boundary_date = AS_OF - timedelta(days=6)
    _seed_momentum_qualifying_data(db_session, instrument, boundary_date)

    result = ScannerService(db_session).scan_symbol("BBCA", AS_OF)

    assert result.skipped_stale is True


def test_scan_symbol_is_value_reproducible_not_just_row_count(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_momentum_qualifying_data(db_session, instrument, AS_OF)
    service = ScannerService(db_session)

    service.scan_symbol("BBCA", AS_OF)
    first_run = {
        c.setup_type: (
            float(c.composite_score),
            float(c.trend_score),
            float(c.risk_reward_score),
        )
        for c in db_session.scalars(select(ScanCandidate)).all()
    }

    service.scan_symbol("BBCA", AS_OF)
    second_run = {
        c.setup_type: (
            float(c.composite_score),
            float(c.trend_score),
            float(c.risk_reward_score),
        )
        for c in db_session.scalars(select(ScanCandidate)).all()
    }

    assert first_run == second_run
    assert len(first_run) > 0


def test_scan_symbol_ignores_split_ingested_after_as_of(db_session) -> None:
    # Mirrors Phase 3's corporate-action look-ahead fix: a split dated
    # after `as_of` must not retroactively adjust prices used in a scan
    # run "as of" a date before that split happened.
    instrument = _seed_instrument(db_session)
    _seed_momentum_qualifying_data(db_session, instrument, AS_OF)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=AS_OF + timedelta(days=30),  # well after as_of
            source="fixture",
            source_symbol=instrument.source_symbol,
            ratio=2.0,
        )
    )
    db_session.commit()

    # capture the raw bar close before scanning
    raw_close = db_session.scalar(
        select(PriceBar.close).where(
            PriceBar.instrument_id == instrument.id, PriceBar.trade_date == AS_OF
        )
    )

    bars = db_session.scalars(select(PriceBar).where(PriceBar.instrument_id == instrument.id)).all()
    corporate_actions = db_session.scalars(
        select(CorporateAction).where(
            CorporateAction.instrument_id == instrument.id, CorporateAction.ex_date <= AS_OF
        )
    ).all()
    snapshots = db_session.scalars(select(IndicatorSnapshot)).all()
    points = build_scan_points(list(bars), list(corporate_actions), list(snapshots))

    # unadjusted: the not-yet-happened split must not have halved the price
    assert points[-1].close == float(raw_close)


def test_scan_symbol_skips_when_indicators_lag_behind_fresh_prices(db_session) -> None:
    # Ingestion (Phase 2) and indicator computation (Phase 3) are separate
    # steps that can drift out of sync: prices keep flowing in fresh, but
    # indicators haven't been (re)computed recently. The bar-only
    # freshness check alone would pass here — this proves the second,
    # scan-date-based check catches it.
    instrument = _seed_instrument(db_session)
    old_date = AS_OF - timedelta(days=10)
    _seed_momentum_qualifying_data(db_session, instrument, old_date)  # bar + snapshot, stale
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=AS_OF,  # fresh bar, no matching indicator snapshot
            open=111.0,
            high=112.0,
            low=110.0,
            close=111.0,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.commit()

    result = ScannerService(db_session).scan_symbol("BBCA", AS_OF)

    assert result.skipped_stale is True
    assert result.candidates_persisted == 0
    assert db_session.scalars(select(ScanCandidate)).all() == []


def test_scan_symbol_no_indicator_snapshot_persists_nothing(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=AS_OF,
            open=110.0,
            high=111.0,
            low=109.0,
            close=110.0,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.commit()

    result = ScannerService(db_session).scan_symbol("BBCA", AS_OF)

    assert result.candidates_persisted == 0


def test_scan_many_records_audit_run(db_session) -> None:
    instrument = _seed_instrument(db_session, "BBCA")
    _seed_momentum_qualifying_data(db_session, instrument, AS_OF)
    stale_instrument = _seed_instrument(db_session, "BBRI")
    _seed_momentum_qualifying_data(db_session, stale_instrument, AS_OF - timedelta(days=30))

    run = ScannerService(db_session).scan_many(["BBCA", "BBRI"], AS_OF)

    assert run.status == ScanStatus.PARTIAL  # one symbol was skipped stale
    assert run.symbols_scanned == 2
    assert run.symbols_skipped_stale == 1
    assert run.candidates_found >= 1
    persisted_run = db_session.scalar(select(ScanRun).where(ScanRun.id == run.id))
    assert persisted_run is not None
    assert persisted_run.finished_at is not None


def test_scan_many_all_fresh_is_succeeded(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_momentum_qualifying_data(db_session, instrument, AS_OF)

    run = ScannerService(db_session).scan_many(["BBCA"], AS_OF)

    assert run.status == ScanStatus.SUCCEEDED
    assert run.symbols_skipped_stale == 0


def test_scan_many_marks_run_failed_on_unseeded_symbol(db_session) -> None:
    with pytest.raises(ValueError, match="not seeded"):
        ScannerService(db_session).scan_many(["NOPE"], AS_OF)

    run = db_session.scalar(select(ScanRun))
    assert run is not None
    assert run.status == ScanStatus.FAILED
    assert run.error_message is not None


def test_scan_candidates_linked_to_scan_run(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_momentum_qualifying_data(db_session, instrument, AS_OF)

    run = ScannerService(db_session).scan_many(["BBCA"], AS_OF)

    candidates = db_session.scalars(select(ScanCandidate)).all()
    assert all(c.scan_run_id == run.id for c in candidates)
