from datetime import UTC, datetime, timedelta

import pytest

from app.db.enums import DataQualityStatus, ExecutionSide, ListingStatus, SetupType, TradePlanStatus
from app.db.models import Instrument, PriceBar, ScanCandidate, TradePlan
from app.positions.execution_service import ExecutionService
from app.positions.performance_service import PerformanceService

T0 = datetime(2024, 1, 1, tzinfo=UTC)
T1 = datetime(2024, 1, 10, tzinfo=UTC)
T2 = datetime(2024, 1, 20, tzinfo=UTC)


def _seed_instrument(db_session, symbol="BBCA", sector="Banking") -> Instrument:
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
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_price_bar(db_session, instrument, trade_date, close) -> None:
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.commit()


def _seed_trade_plan_with_candidate(
    db_session, instrument, *, entry_price=1000.0, stop_price=950.0, quantity=100, score=75.0
) -> TradePlan:
    candidate = ScanCandidate(
        instrument_id=instrument.id,
        scan_date=T0.date(),
        setup_type=SetupType.BREAKOUT,
        indicator_version="v1",
        score_version="v1",
        composite_score=score,
        trend_score=0,
        momentum_score=0,
        volume_score=0,
        price_structure_score=0,
        volatility_score=0,
        setup_quality_score=0,
        risk_reward_score=0,
        qualifying_conditions=["test"],
        invalidation_conditions=[],
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)

    plan = TradePlan(
        instrument_id=instrument.id,
        scan_candidate_id=candidate.id,
        setup_type=SetupType.BREAKOUT,
        plan_date=T0.date(),
        risk_version="v1",
        status=TradePlanStatus.VALID,
        rejection_reasons=[],
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=[1100.0],
        quantity=quantity,
        allocation_amount=100_000.0,
        allocation_pct=0.1,
        max_loss_amount=5_000.0,
        assumptions={"capital": 1_000_000.0},
        invalidation_conditions=[],
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def test_equity_curve_reflects_only_sells_cumulative(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )

    curve = PerformanceService(db_session).equity_curve(initial_capital=0.0)
    assert len(curve) == 1
    assert curve[0][0] == T1.date()
    assert curve[0][1] == pytest.approx(10_000.0)


def test_equity_curve_cumulative_across_multiple_closed_positions(db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA")
    _seed_instrument(db_session, symbol="BBRI")
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    service.record_execution(
        symbol="BBRI", side=ExecutionSide.BUY, quantity=50, price=500.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBRI", side=ExecutionSide.SELL, quantity=50, price=400.0, fee=0.0, executed_at=T2
    )

    curve = PerformanceService(db_session).equity_curve(initial_capital=1_000_000.0)
    assert len(curve) == 2
    assert curve[0][1] == pytest.approx(1_000_000.0 + 10_000.0)
    assert curve[1][1] == pytest.approx(1_000_000.0 + 10_000.0 - 5_000.0)


def test_summary_no_look_ahead_unrealized_pnl_uses_latest_close_not_future(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_bar(db_session, instrument, T0.date(), 1000.0)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )

    summary_before = PerformanceService(db_session).summary()
    assert summary_before.unrealized_pnl == pytest.approx(0.0)  # no price movement yet

    # a later, wildly different bar is added — unrealized P&L must pick
    # up the LATEST available close, not a stale or fabricated value
    _seed_price_bar(db_session, instrument, T0.date() + timedelta(days=1), 1500.0)
    summary_after = PerformanceService(db_session).summary()
    assert summary_after.unrealized_pnl == pytest.approx(100 * (1500.0 - 1000.0))


def test_summary_exposure_uses_cost_basis(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    summary = PerformanceService(db_session).summary()
    assert summary.exposure == pytest.approx(100_000.0)


def test_summary_win_rate_and_profit_factor(db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA")
    _seed_instrument(db_session, symbol="BBRI")
    service = ExecutionService(db_session)
    # a win
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    # a loss
    service.record_execution(
        symbol="BBRI", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBRI", side=ExecutionSide.SELL, quantity=100, price=900.0, fee=0.0, executed_at=T1
    )

    summary = PerformanceService(db_session).summary()
    assert summary.closed_position_count == 2
    assert summary.win_rate_pct == pytest.approx(50.0)
    assert summary.profit_factor == pytest.approx(10_000.0 / 10_000.0)


def test_by_setup_groups_correctly(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan_with_candidate(db_session, instrument)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.BUY,
        quantity=100,
        price=1000.0,
        fee=0.0,
        executed_at=T0,
        trade_plan_id=plan.id,
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )

    groups = PerformanceService(db_session).by_setup()
    assert len(groups) == 1
    assert groups[0].key == "BREAKOUT"
    assert groups[0].closed_position_count == 1
    assert groups[0].total_realized_pnl == pytest.approx(10_000.0)


def test_by_setup_none_bucket_for_positions_without_linked_plan(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )

    groups = PerformanceService(db_session).by_setup()
    assert len(groups) == 1
    assert groups[0].key is None


def test_by_sector_groups_correctly(db_session) -> None:
    _seed_instrument(db_session, sector="Banking")
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    groups = PerformanceService(db_session).by_sector()
    assert groups[0].key == "Banking"


def test_by_holding_period_buckets_correctly(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    # held 9 days -> bucket "6-10d"
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    groups = PerformanceService(db_session).by_holding_period()
    assert groups[0].key == "6-10d"


def test_by_holding_period_boundary_exactly_5_days_in_lower_bucket(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    # held exactly 5 days -> boundary of the "0-5d" bucket, not "6-10d"
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.SELL,
        quantity=100,
        price=1100.0,
        fee=0.0,
        executed_at=T0 + timedelta(days=5),
    )
    groups = PerformanceService(db_session).by_holding_period()
    assert groups[0].key == "0-5d"


def test_by_holding_period_boundary_exactly_6_days_in_next_bucket(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.SELL,
        quantity=100,
        price=1100.0,
        fee=0.0,
        executed_at=T0 + timedelta(days=6),
    )
    groups = PerformanceService(db_session).by_holding_period()
    assert groups[0].key == "6-10d"


def test_by_holding_period_open_ended_bucket_beyond_21_days(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.SELL,
        quantity=100,
        price=1100.0,
        fee=0.0,
        executed_at=T0 + timedelta(days=100),
    )
    groups = PerformanceService(db_session).by_holding_period()
    assert groups[0].key == "21+d"


def test_unrealized_pnl_only_reflects_positions_with_price_data(db_session) -> None:
    """A position with no PriceBar at all must not contribute a
    fabricated gain/loss to unrealized P&L, while its cost basis still
    counts toward exposure (exposure doesn't depend on a market price).
    Uses two instruments so the priced one's real contribution proves
    the unpriced one wasn't silently treated as a zero-movement price."""
    instrument_priced = _seed_instrument(db_session, symbol="BBCA")
    _seed_instrument(db_session, symbol="BBRI")  # no PriceBar seeded for this one
    _seed_price_bar(db_session, instrument_priced, T0.date(), 1000.0)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBRI", side=ExecutionSide.BUY, quantity=50, price=500.0, fee=0.0, executed_at=T0
    )

    # move BBCA's price so it has a real, known unrealized gain
    _seed_price_bar(db_session, instrument_priced, T0.date() + timedelta(days=1), 1200.0)
    summary = PerformanceService(db_session).summary()

    assert summary.unrealized_pnl == pytest.approx(100 * (1200.0 - 1000.0))  # BBRI contributed 0
    assert summary.exposure == pytest.approx(100_000.0 + 25_000.0)  # both cost bases counted


def test_summary_reproducible_identical_inputs_identical_output(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=10.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=10.0, executed_at=T1
    )
    perf = PerformanceService(db_session)
    first = perf.summary()
    second = perf.summary()
    assert first == second


def test_by_score_bucket_groups_correctly(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan_with_candidate(db_session, instrument, score=85.0)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.BUY,
        quantity=100,
        price=1000.0,
        fee=0.0,
        executed_at=T0,
        trade_plan_id=plan.id,
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    groups = PerformanceService(db_session).by_score_bucket()
    assert groups[0].key == "80-100"


def test_behavior_stop_violated_true_when_exit_worse_than_planned_stop(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan_with_candidate(db_session, instrument, stop_price=950.0)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.BUY,
        quantity=100,
        price=1000.0,
        fee=0.0,
        executed_at=T0,
        trade_plan_id=plan.id,
    )
    # exits at 900, worse than the planned stop of 950
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=900.0, fee=0.0, executed_at=T1
    )

    entries = PerformanceService(db_session).behavior()
    assert len(entries) == 1
    assert entries[0].stop_violated is True


def test_behavior_stop_not_violated_when_exit_better_than_planned_stop(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan_with_candidate(db_session, instrument, stop_price=950.0)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.BUY,
        quantity=100,
        price=1000.0,
        fee=0.0,
        executed_at=T0,
        trade_plan_id=plan.id,
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    entries = PerformanceService(db_session).behavior()
    assert entries[0].stop_violated is False


def test_behavior_none_when_no_linked_plan(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    entries = PerformanceService(db_session).behavior()
    assert entries[0].stop_violated is None
    assert entries[0].entry_deviation_pct is None
    assert entries[0].quantity_deviation_pct is None


def test_behavior_entry_and_quantity_deviation(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan_with_candidate(db_session, instrument, entry_price=1000.0, quantity=100)
    service = ExecutionService(db_session)
    # actual entry at 1050 (5% worse) with only 80 shares (20% less than planned)
    service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.BUY,
        quantity=80,
        price=1050.0,
        fee=0.0,
        executed_at=T0,
        trade_plan_id=plan.id,
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=80, price=1100.0, fee=0.0, executed_at=T1
    )
    entries = PerformanceService(db_session).behavior()
    assert entries[0].entry_deviation_pct == pytest.approx(5.0)
    assert entries[0].quantity_deviation_pct == pytest.approx(-20.0)
