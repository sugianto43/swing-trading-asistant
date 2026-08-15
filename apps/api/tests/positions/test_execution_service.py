from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.db.enums import ExecutionSide, ListingStatus, PositionStatus, SetupType, TradePlanStatus
from app.db.models import Execution, Instrument, Position, TradePlan
from app.positions.execution_service import ExecutionService

T0 = datetime(2024, 1, 1, tzinfo=UTC)
T1 = datetime(2024, 1, 5, tzinfo=UTC)


def _seed_instrument(db_session, symbol: str = "BBCA") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Test Co",
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


def _seed_trade_plan(
    db_session, instrument: Instrument, *, status=TradePlanStatus.VALID, plan_date=None
) -> TradePlan:
    plan = TradePlan(
        instrument_id=instrument.id,
        setup_type=SetupType.BREAKOUT,
        plan_date=plan_date or T0.date(),
        risk_version="v1",
        status=status,
        rejection_reasons=[],
        entry_price=1000.0,
        stop_price=950.0,
        target_prices=[1100.0],
        quantity=100,
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


def test_record_buy_creates_open_position_and_execution_row(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)

    position = service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=50.0, executed_at=T0
    )

    assert position.status == PositionStatus.OPEN
    assert position.quantity_open == 100
    assert float(position.avg_entry_price) == 1000.0

    executions = db_session.scalars(select(Execution)).all()
    assert len(executions) == 1
    assert executions[0].side == ExecutionSide.BUY
    assert executions[0].realized_pnl_impact is None


def test_record_sell_updates_position_and_stores_pnl_impact(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    position = service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )

    assert position.status == PositionStatus.CLOSED
    assert float(position.realized_pnl) == pytest.approx(10_000.0)

    sell_execution = db_session.scalar(
        select(Execution).where(Execution.side == ExecutionSide.SELL)
    )
    assert float(sell_execution.realized_pnl_impact) == pytest.approx(10_000.0)


def test_executions_are_never_updated_only_new_rows_inserted(db_session) -> None:
    """Structural check for append-only: recording two BUYs must produce
    two Execution rows, not one row mutated twice."""
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=50, price=1000.0, fee=0.0, executed_at=T0
    )
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=50, price=1100.0, fee=0.0, executed_at=T1
    )
    executions = db_session.scalars(select(Execution)).all()
    assert len(executions) == 2
    # never mutated: each row keeps its own original price
    prices = sorted(float(e.price) for e in executions)
    assert prices == [1000.0, 1100.0]


def test_unknown_symbol_raises(db_session) -> None:
    service = ExecutionService(db_session)
    with pytest.raises(ValueError, match="not seeded"):
        service.record_execution(
            symbol="NOPE", side=ExecutionSide.BUY, quantity=1, price=1.0, fee=0.0, executed_at=T0
        )


def test_zero_quantity_rejected(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    with pytest.raises(ValueError, match="quantity must be positive"):
        service.record_execution(
            symbol="BBCA", side=ExecutionSide.BUY, quantity=0, price=1000.0, fee=0.0, executed_at=T0
        )


def test_negative_price_rejected(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    with pytest.raises(ValueError, match="price must be positive"):
        service.record_execution(
            symbol="BBCA", side=ExecutionSide.BUY, quantity=1, price=-1.0, fee=0.0, executed_at=T0
        )


def test_negative_fee_rejected(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    with pytest.raises(ValueError, match="fee cannot be negative"):
        service.record_execution(
            symbol="BBCA",
            side=ExecutionSide.BUY,
            quantity=1,
            price=1000.0,
            fee=-1.0,
            executed_at=T0,
        )


def test_sell_exceeding_open_quantity_rejected(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=50, price=1000.0, fee=0.0, executed_at=T0
    )
    with pytest.raises(ValueError, match="cannot sell"):
        service.record_execution(
            symbol="BBCA",
            side=ExecutionSide.SELL,
            quantity=100,
            price=1000.0,
            fee=0.0,
            executed_at=T1,
        )


def test_create_planned_position_from_valid_trade_plan(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument)
    service = ExecutionService(db_session)

    position = service.create_planned_position(plan.id)
    assert position.status == PositionStatus.PLANNED
    assert position.trade_plan_id == plan.id
    assert position.quantity_open == 0


def test_create_planned_position_from_rejected_trade_plan_rejected(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument, status=TradePlanStatus.REJECTED)
    service = ExecutionService(db_session)

    with pytest.raises(ValueError, match="REJECTED"):
        service.create_planned_position(plan.id)


def test_create_planned_position_unknown_plan_raises(db_session) -> None:
    service = ExecutionService(db_session)
    with pytest.raises(ValueError, match="not found"):
        service.create_planned_position(__import__("uuid").uuid4())


def test_create_planned_position_rejects_when_non_terminal_position_exists(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument)
    service = ExecutionService(db_session)
    service.create_planned_position(plan.id)

    plan2 = _seed_trade_plan(db_session, instrument, plan_date=T1.date())
    with pytest.raises(ValueError, match="non-terminal position"):
        service.create_planned_position(plan2.id)


def test_buy_transitions_planned_position_to_open(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument)
    service = ExecutionService(db_session)
    planned = service.create_planned_position(plan.id)

    opened = service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    assert opened.id == planned.id  # same position row transitioned, not a new one
    assert opened.status == PositionStatus.OPEN
    assert opened.trade_plan_id == plan.id


def test_cancel_planned_position(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument)
    service = ExecutionService(db_session)
    planned = service.create_planned_position(plan.id)

    cancelled = service.cancel_position(planned.id)
    assert cancelled.status == PositionStatus.CANCELLED


def test_cancel_open_position_rejected(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    position = service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    with pytest.raises(ValueError, match="only a PLANNED position"):
        service.cancel_position(position.id)


def test_cancel_unknown_position_raises(db_session) -> None:
    service = ExecutionService(db_session)
    with pytest.raises(ValueError, match="not found"):
        service.cancel_position(__import__("uuid").uuid4())


def test_reopening_after_closed_creates_new_position_row(db_session) -> None:
    _seed_instrument(db_session)
    service = ExecutionService(db_session)
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )
    closed = service.record_execution(
        symbol="BBCA", side=ExecutionSide.SELL, quantity=100, price=1100.0, fee=0.0, executed_at=T1
    )
    reopened = service.record_execution(
        symbol="BBCA",
        side=ExecutionSide.BUY,
        quantity=50,
        price=900.0,
        fee=0.0,
        executed_at=datetime(2024, 1, 10, tzinfo=UTC),
    )
    assert reopened.id != closed.id
    all_positions = db_session.scalars(select(Position)).all()
    assert len(all_positions) == 2


def test_record_execution_concurrent_position_creation_race_rejected(db_session) -> None:
    """Regression for the fix-phase HIGH finding: if the 'does a
    non-terminal position already exist' lookup returns a stale None
    (another request committed one in between), the resulting
    IntegrityError from the partial unique index must be caught and
    turned into a clean ValueError, not surfaced as a raw crash."""
    _seed_instrument(db_session)
    service = ExecutionService(db_session)

    # a real, already-committed OPEN position for this instrument
    service.record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )

    real_scalar = db_session.scalar
    call_count = {"n": 0}

    def flaky_scalar(*args, **kwargs):
        call_count["n"] += 1
        # call 1 is the Instrument lookup (must succeed); call 2 is the
        # non-terminal-position lookup — force a stale None on that one
        if call_count["n"] == 2:
            return None
        return real_scalar(*args, **kwargs)

    with patch.object(db_session, "scalar", side_effect=flaky_scalar):
        with pytest.raises(ValueError, match="concurrently"):
            service.record_execution(
                symbol="BBCA",
                side=ExecutionSide.BUY,
                quantity=50,
                price=1000.0,
                fee=0.0,
                executed_at=T1,
            )

    # the race attempt must not have left a stray second Position row
    all_positions = db_session.scalars(select(Position)).all()
    assert len(all_positions) == 1


def test_create_planned_position_concurrent_creation_race_rejected(db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument)
    service = ExecutionService(db_session)
    service.create_planned_position(plan.id)

    plan2 = _seed_trade_plan(db_session, instrument, plan_date=T1.date())
    real_scalar = db_session.scalar
    call_count = {"n": 0}

    def flaky_scalar(*args, **kwargs):
        call_count["n"] += 1
        # the first two scalar() calls inside create_planned_position are
        # the trade-plan lookup (must succeed) and the non-terminal
        # position lookup (force a stale None on this one)
        if call_count["n"] == 2:
            return None
        return real_scalar(*args, **kwargs)

    with patch.object(db_session, "scalar", side_effect=flaky_scalar):
        with pytest.raises(ValueError, match="concurrently"):
            service.create_planned_position(plan2.id)

    all_positions = db_session.scalars(select(Position)).all()
    assert len(all_positions) == 1
