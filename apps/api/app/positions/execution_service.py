import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.enums import ExecutionSide, PositionStatus, TradePlanStatus
from app.db.models import Execution, Instrument, Position, TradePlan
from app.positions.position_engine import (
    ApplyExecutionResult,
    ExecutionInput,
    PositionState,
    apply_execution_to_position,
    cancel_planned_state,
    new_planned_state,
)

_NON_TERMINAL = (PositionStatus.PLANNED, PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED)


def _to_state(position: Position) -> PositionState:
    return PositionState(
        status=position.status,
        trade_plan_id=position.trade_plan_id,
        quantity_open=position.quantity_open,
        avg_entry_price=float(position.avg_entry_price)
        if position.avg_entry_price is not None
        else None,
        avg_entry_fee_per_share=float(position.avg_entry_fee_per_share),
        cumulative_quantity_bought=position.cumulative_quantity_bought,
        cumulative_entry_fees=float(position.cumulative_entry_fees),
        cumulative_exit_fees=float(position.cumulative_exit_fees),
        realized_pnl=float(position.realized_pnl),
        opened_at=position.opened_at,
        closed_at=position.closed_at,
    )


def _apply_state(position: Position, state: PositionState) -> None:
    position.status = state.status
    position.trade_plan_id = state.trade_plan_id
    position.quantity_open = state.quantity_open
    position.avg_entry_price = state.avg_entry_price
    position.avg_entry_fee_per_share = state.avg_entry_fee_per_share
    position.cumulative_quantity_bought = state.cumulative_quantity_bought
    position.cumulative_entry_fees = state.cumulative_entry_fees
    position.cumulative_exit_fees = state.cumulative_exit_fees
    position.realized_pnl = state.realized_pnl
    position.opened_at = state.opened_at
    position.closed_at = state.closed_at


class ExecutionService:
    """Records executions (append-only) and drives Position state in the
    same transaction. At most one non-terminal (PLANNED/OPEN/
    PARTIALLY_CLOSED) Position may exist per instrument — checked here
    up front for a clean error on the common case, and backed by a real
    partial unique index (Position.uq_positions_one_non_terminal_per_instrument)
    so a race between two concurrent requests can't silently create two
    non-terminal positions for the same instrument; the resulting
    IntegrityError is caught and re-raised as the same ValueError."""

    def __init__(self, session: Session):
        self.session = session

    def _find_non_terminal_position(self, instrument_id: uuid.UUID) -> Position | None:
        return self.session.scalar(
            select(Position).where(
                Position.instrument_id == instrument_id, Position.status.in_(_NON_TERMINAL)
            )
        )

    def create_planned_position(self, trade_plan_id: uuid.UUID) -> Position:
        trade_plan = self.session.scalar(select(TradePlan).where(TradePlan.id == trade_plan_id))
        if trade_plan is None:
            raise ValueError(f"trade plan not found: {trade_plan_id}")
        if trade_plan.status != TradePlanStatus.VALID:
            raise ValueError("cannot plan a position from a REJECTED trade plan")

        existing = self._find_non_terminal_position(trade_plan.instrument_id)
        if existing is not None:
            raise ValueError(
                f"instrument already has a non-terminal position (status={existing.status.value})"
            )

        state = new_planned_state(trade_plan_id)
        position = Position(instrument_id=trade_plan.instrument_id)
        _apply_state(position, state)
        self.session.add(position)
        try:
            self.session.commit()
        except IntegrityError as exc:
            # a concurrent request for the same instrument won the race
            # between our SELECT above and this INSERT — the DB-level
            # partial unique index caught what the earlier check alone
            # could have silently missed.
            self.session.rollback()
            raise ValueError(
                "instrument already has a non-terminal position (created concurrently)"
            ) from exc
        self.session.refresh(position)
        return position

    def cancel_position(self, position_id: uuid.UUID) -> Position:
        position = self.session.scalar(select(Position).where(Position.id == position_id))
        if position is None:
            raise ValueError(f"position not found: {position_id}")

        state = cancel_planned_state(_to_state(position))
        _apply_state(position, state)
        self.session.commit()
        self.session.refresh(position)
        return position

    def record_execution(
        self,
        symbol: str,
        side: ExecutionSide,
        quantity: int,
        price: float,
        fee: float,
        executed_at: datetime,
        trade_plan_id: uuid.UUID | None = None,
        notes: str | None = None,
    ) -> Position:
        instrument = self.session.scalar(select(Instrument).where(Instrument.symbol == symbol))
        if instrument is None:
            raise ValueError(f"instrument not seeded: {symbol!r}")
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if price <= 0:
            raise ValueError("price must be positive")
        if fee < 0:
            raise ValueError("fee cannot be negative")

        existing = self._find_non_terminal_position(instrument.id)
        current_state = _to_state(existing) if existing is not None else None

        execution_input = ExecutionInput(
            instrument_id=instrument.id,
            side=side,
            quantity=quantity,
            price=price,
            fee=fee,
            executed_at=executed_at,
            trade_plan_id=trade_plan_id,
            notes=notes,
        )
        result: ApplyExecutionResult = apply_execution_to_position(current_state, execution_input)

        if existing is not None:
            position = existing
        else:
            position = Position(instrument_id=instrument.id)
            self.session.add(position)
        _apply_state(position, result.new_state)
        try:
            self.session.flush()  # populate position.id before the Execution FK references it
        except IntegrityError as exc:
            # same concurrent-creation race as create_planned_position:
            # another request opened a non-terminal position for this
            # instrument between our SELECT and this INSERT. Reject
            # cleanly rather than recording an execution against a
            # position state we know is now stale — the caller can retry.
            self.session.rollback()
            raise ValueError(
                "instrument already has a non-terminal position (created concurrently) — retry"
            ) from exc

        execution = Execution(
            position_id=position.id,
            instrument_id=instrument.id,
            trade_plan_id=trade_plan_id or position.trade_plan_id,
            side=side,
            quantity=quantity,
            price=price,
            fee=fee,
            realized_pnl_impact=result.realized_pnl_impact,
            executed_at=executed_at,
            notes=notes,
        )
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(position)
        return position
