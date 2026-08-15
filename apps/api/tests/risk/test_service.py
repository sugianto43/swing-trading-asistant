from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.db.enums import DataQualityStatus, ListingStatus, SetupType, TradePlanStatus
from app.db.models import (
    IndicatorSnapshot,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
    ScanCandidate,
    TradePlan,
)
from app.indicators.versioning import INDICATOR_VERSION
from app.risk.config import RiskConfig
from app.risk.engine import PortfolioPosition, TradePlanResult
from app.risk.service import RiskService
from app.scanner.scoring_config import SCORE_VERSION

PLAN_DATE = date(2024, 3, 1)


def _seed_instrument(
    db_session, symbol: str = "BBCA", sector: str | None = "Banking"
) -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        sector=sector,
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.flush()
    db_session.add(
        InstrumentStatusHistory(
            instrument_id=instrument.id,
            status=ListingStatus.ACTIVE,
            effective_from=datetime(2020, 1, 1, tzinfo=UTC),
            source="fixture",
        )
    )
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_price_and_indicator(db_session, instrument: Instrument, plan_date: date) -> None:
    for i in range(5):
        trade_date = plan_date - timedelta(days=4 - i)
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=1000.0,
                high=1010.0,
                low=990.0,
                close=1000.0,
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
                indicator_version=INDICATOR_VERSION,
                atr_14=20.0,
                volume_sma_20=1_000_000.0,
            )
        )
    db_session.commit()


def _seed_scan_candidate(db_session, instrument: Instrument, plan_date: date) -> ScanCandidate:
    candidate = ScanCandidate(
        instrument_id=instrument.id,
        scan_date=plan_date,
        setup_type=SetupType.BREAKOUT,
        indicator_version=INDICATOR_VERSION,
        score_version=SCORE_VERSION,
        composite_score=80.0,
        trend_score=0,
        momentum_score=0,
        volume_score=0,
        price_structure_score=0,
        volatility_score=0,
        setup_quality_score=0,
        risk_reward_score=0,
        qualifying_conditions=["test"],
        invalidation_conditions=["close below breakout level"],
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate


def test_build_plan_persists_valid_trade_plan(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, PLAN_DATE)
    candidate = _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    service = RiskService(db_session)
    plan = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )

    assert plan.status == TradePlanStatus.VALID
    assert plan.scan_candidate_id == candidate.id
    assert plan.invalidation_conditions == ["close below breakout level"]
    assert plan.risk_version == RiskConfig().risk_version

    persisted = db_session.scalar(select(TradePlan).where(TradePlan.id == plan.id))
    assert persisted is not None


def test_build_plan_rejected_when_no_scan_candidate(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, PLAN_DATE)

    service = RiskService(db_session)
    plan = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )

    assert plan.status == TradePlanStatus.REJECTED
    assert any("no qualifying scan candidate" in r for r in plan.rejection_reasons)


def test_build_plan_rejected_when_no_price_data(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    service = RiskService(db_session)
    plan = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )

    assert plan.status == TradePlanStatus.REJECTED
    assert any("no price/indicator data" in r for r in plan.rejection_reasons)


def test_build_plan_unknown_symbol_raises(db_session) -> None:
    service = RiskService(db_session)
    with pytest.raises(ValueError, match="instrument not seeded"):
        service.build_plan(
            symbol="NOPE", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=1.0
        )


def test_build_plan_is_idempotent_upsert_by_natural_key(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, PLAN_DATE)
    _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    service = RiskService(db_session)
    first = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )
    second = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=200_000_000.0
    )

    assert first.id == second.id  # same row updated, not duplicated
    all_plans = db_session.scalars(select(TradePlan)).all()
    assert len(all_plans) == 1
    assert second.assumptions["capital"] == 200_000_000.0


def test_build_plan_respects_existing_portfolio_concentration(db_session) -> None:
    instrument = _seed_instrument(db_session, symbol="BBCA", sector="Banking")
    _seed_price_and_indicator(db_session, instrument, PLAN_DATE)
    _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    config = RiskConfig(max_sector_exposure_pct=0.05)
    existing_positions = [
        PortfolioPosition(symbol="OTHER", sector="Banking", allocation_amount=90_000_000.0)
    ]
    service = RiskService(db_session)
    plan = service.build_plan(
        symbol="BBCA",
        setup_type=SetupType.BREAKOUT,
        plan_date=PLAN_DATE,
        capital=100_000_000.0,
        existing_positions=existing_positions,
        config=config,
    )

    assert plan.status == TradePlanStatus.REJECTED
    assert any("sector exposure" in r for r in plan.rejection_reasons)


def test_build_plan_no_look_ahead_future_mutation(db_session) -> None:
    """A trade plan for PLAN_DATE must not change when data strictly
    after PLAN_DATE is mutated — mirrors the adversarial pattern used in
    Phase 5's no-look-ahead tests."""
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, PLAN_DATE)
    _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    service = RiskService(db_session)
    baseline = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )
    baseline_quantity = baseline.quantity
    baseline_stop = float(baseline.stop_price)

    # add a wildly different future bar/indicator snapshot after PLAN_DATE
    future_date = PLAN_DATE + timedelta(days=5)
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=future_date,
            open=9999.0,
            high=9999.0,
            low=9999.0,
            close=9999.0,
            volume=1,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id,
            trade_date=future_date,
            indicator_version=INDICATOR_VERSION,
            atr_14=9999.0,
            volume_sma_20=1.0,
        )
    )
    db_session.commit()

    # re-run the same symbol/setup/date/config now that future data exists
    replay = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )

    assert replay.quantity == baseline_quantity
    assert float(replay.stop_price) == baseline_stop


def test_build_plan_reproducible_identical_values_on_rerun(db_session) -> None:
    """Same symbol/setup/date/capital/config re-run twice (different
    session-level calls) must produce byte-identical computed fields —
    not merely 'a plan exists', but the same numbers (QUANT-TRADING-RULES
    reproducibility requirement)."""
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, PLAN_DATE)
    _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    service = RiskService(db_session)
    first = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )
    first_values = (
        first.quantity,
        float(first.stop_price),
        float(first.entry_price),
        list(first.target_prices),
        float(first.allocation_amount),
        float(first.risk_reward_ratio),
    )

    second = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )
    second_values = (
        second.quantity,
        float(second.stop_price),
        float(second.entry_price),
        list(second.target_prices),
        float(second.allocation_amount),
        float(second.risk_reward_ratio),
    )

    assert first_values == second_values


def test_build_plan_rejected_when_price_bar_present_but_indicator_missing(db_session) -> None:
    """A date with a price bar but no computed indicator snapshot (Phase
    3 not yet run for that date) must be treated as missing data, never
    fabricated — build_scan_points silently drops such a date, and the
    service must surface that as a rejection, not a crash or a fake
    plan."""
    instrument = _seed_instrument(db_session)
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=PLAN_DATE,
            open=1000.0,
            high=1010.0,
            low=990.0,
            close=1000.0,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.commit()
    _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    service = RiskService(db_session)
    plan = service.build_plan(
        symbol="BBCA", setup_type=SetupType.BREAKOUT, plan_date=PLAN_DATE, capital=100_000_000.0
    )

    assert plan.status == TradePlanStatus.REJECTED
    assert any("no price/indicator data" in r for r in plan.rejection_reasons)


def test_build_plan_boundary_capital_affords_exactly_one_lot(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, PLAN_DATE)
    _seed_scan_candidate(db_session, instrument, PLAN_DATE)

    config = RiskConfig(risk_per_trade_pct=1.0, fee_bps=0.0)  # risk budget won't bind sizing
    lot_size = config.lot_size
    # capital sized to afford exactly one lot at the slippage-adjusted
    # entry price, no more
    entry_with_slippage = 1000.0 * (1 + config.slippage_bps / 10_000)
    capital = entry_with_slippage * lot_size

    service = RiskService(db_session)
    plan = service.build_plan(
        symbol="BBCA",
        setup_type=SetupType.BREAKOUT,
        plan_date=PLAN_DATE,
        capital=capital,
        config=config,
    )

    assert plan.quantity == lot_size


def test_persist_concurrent_duplicate_insert_falls_back_to_update(db_session) -> None:
    """Regression for the fix-phase MEDIUM finding: if the 'does a plan
    already exist' lookup returns a stale None (the classic
    check-then-insert race — another request committed the same natural
    key in between), the resulting IntegrityError on insert must be
    caught and turned into an update, not surfaced as a raw 500."""
    instrument = _seed_instrument(db_session)
    config = RiskConfig()
    service = RiskService(db_session)
    reject_result = TradePlanResult(valid=False, rejection_reasons=["no data"])

    # first call creates the row normally, exercising the plain insert path
    first = service._persist(
        instrument.id,
        None,
        SetupType.BREAKOUT,
        PLAN_DATE,
        config,
        reject_result,
        score_version=None,
        indicator_version=None,
        assumptions={"capital": 1.0},
        invalidation_conditions=[],
    )

    # simulate a racing second request: its own "does this already
    # exist" lookup sees a stale None even though `first` already
    # committed, so it attempts an INSERT that collides with the real
    # unique constraint (instrument_id, plan_date, setup_type,
    # risk_version) and must recover instead of raising.
    real_scalar = db_session.scalar
    call_count = {"n": 0}

    def flaky_scalar(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return real_scalar(*args, **kwargs)

    with patch.object(db_session, "scalar", side_effect=flaky_scalar):
        second = service._persist(
            instrument.id,
            None,
            SetupType.BREAKOUT,
            PLAN_DATE,
            config,
            reject_result,
            score_version=None,
            indicator_version=None,
            assumptions={"capital": 2.0},
            invalidation_conditions=[],
        )

    assert second.id == first.id  # same row updated, not a duplicate / a crash
    all_plans = db_session.scalars(select(TradePlan)).all()
    assert len(all_plans) == 1
    assert second.assumptions["capital"] == 2.0
