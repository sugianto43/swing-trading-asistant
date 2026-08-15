"""Deterministic position-state machine: append-only execution ledger ->
current position state. Pure functions only, no DB access — same
discipline as app/risk/engine.py and app/backtesting/simulator.py.

Long-only model: BUY opens/adds to a position, SELL reduces/closes it.
Short-selling isn't modeled (not broadly available to IDX retail traders,
the stated persona) — a SELL against no open quantity is rejected, never
silently treated as opening a short.

Reopening after CLOSED/CANCELLED is modeled as a brand-new Position row
(current=None going in), not a reuse of the old one — a position's
lifecycle is one pass through PLANNED/OPEN/PARTIALLY_CLOSED/CLOSED, not a
loop. Callers (ExecutionService) are responsible for finding the correct
existing non-terminal Position (if any) for an instrument before calling
into this module.
"""

import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from app.db.enums import ExecutionSide, PositionStatus


@dataclass(frozen=True, slots=True)
class ExecutionInput:
    instrument_id: uuid.UUID
    side: ExecutionSide
    quantity: int
    price: float
    fee: float
    executed_at: datetime
    trade_plan_id: uuid.UUID | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class PositionState:
    """Mirrors the persisted Position row's business fields. `None` (no
    state) represents "no existing position for this instrument".

    avg_entry_fee_per_share is tracked with the exact same weighted-average
    discipline as avg_entry_price (recomputed on every BUY, untouched by a
    SELL) — see apply_execution_to_position's docstring for why this
    replaced apportioning fees off cumulative_entry_fees/
    cumulative_quantity_bought, which drifted whenever a BUY followed a
    partial SELL on the same position.
    """

    status: PositionStatus
    trade_plan_id: uuid.UUID | None
    quantity_open: int
    avg_entry_price: float | None
    avg_entry_fee_per_share: float
    cumulative_quantity_bought: int
    cumulative_entry_fees: float
    cumulative_exit_fees: float
    realized_pnl: float
    opened_at: datetime | None
    closed_at: datetime | None


@dataclass(frozen=True, slots=True)
class ApplyExecutionResult:
    new_state: PositionState
    # the P&L this SPECIFIC execution realized — None for a BUY (entries
    # never realize P&L) or when there's nothing to attribute yet.
    realized_pnl_impact: float | None


def new_planned_state(trade_plan_id: uuid.UUID) -> PositionState:
    return PositionState(
        status=PositionStatus.PLANNED,
        trade_plan_id=trade_plan_id,
        quantity_open=0,
        avg_entry_price=None,
        avg_entry_fee_per_share=0.0,
        cumulative_quantity_bought=0,
        cumulative_entry_fees=0.0,
        cumulative_exit_fees=0.0,
        realized_pnl=0.0,
        opened_at=None,
        closed_at=None,
    )


def cancel_planned_state(current: PositionState) -> PositionState:
    if current.status != PositionStatus.PLANNED:
        raise ValueError("only a PLANNED position (no executions yet) can be cancelled")
    return replace(current, status=PositionStatus.CANCELLED)


def _weighted_avg_entry(
    prior_quantity: int, prior_avg_price: float | None, add_quantity: int, add_price: float
) -> float:
    prior_cost = prior_quantity * (prior_avg_price or 0.0)
    return (prior_cost + add_quantity * add_price) / (prior_quantity + add_quantity)


def apply_execution_to_position(
    current: PositionState | None, execution: ExecutionInput
) -> ApplyExecutionResult:
    """Applies one execution to the current position state, returning the
    new state and (for a SELL) the realized P&L this execution produced.

    Fee apportionment on partial exits: avg_entry_fee_per_share tracks the
    average entry fee cost of currently-held shares, weighted-averaged on
    every BUY the exact same way avg_entry_price is (and, like
    avg_entry_price, untouched by a SELL). Each SELL apportions
    `avg_entry_fee_per_share * quantity_sold` immediately, plus its own
    exit fee in full.

    An earlier version apportioned off cumulative_entry_fees /
    cumulative_quantity_bought (both all-time running totals) instead.
    That formula silently lost money whenever a BUY followed a partial
    SELL on the same position: a later BUY grows the denominator
    (cumulative_quantity_bought) retroactively, so a SELL's fee share
    computed against the OLD, smaller denominator never gets reconciled
    against the fee paid on shares bought afterward — some entry fee
    ends up permanently unapportioned. Tracking a running per-share
    average (mirroring avg_entry_price, which has always been correct
    for the identical reason) fixes this: the sum of every SELL's
    apportioned share always equals the sum of every BUY's fee, exactly,
    regardless of how BUYs and SELLs interleave.

    realized_pnl for a SELL of `q` shares at price `p`, fee `f`:
        entry_fee_share = avg_entry_fee_per_share * q
        pnl = (p - avg_entry_price) * q - entry_fee_share - f
    """
    is_terminal_or_new = current is None or current.status in (
        PositionStatus.CLOSED,
        PositionStatus.CANCELLED,
    )

    if execution.side == ExecutionSide.BUY:
        base = None if is_terminal_or_new else current
        prior_quantity = base.quantity_open if base else 0
        prior_avg_price = base.avg_entry_price if base else None
        prior_avg_fee_per_share = base.avg_entry_fee_per_share if base else 0.0
        prior_bought = base.cumulative_quantity_bought if base else 0
        prior_entry_fees = base.cumulative_entry_fees if base else 0.0
        prior_exit_fees = base.cumulative_exit_fees if base else 0.0
        prior_realized_pnl = base.realized_pnl if base else 0.0
        opened_at = base.opened_at if base and base.opened_at else execution.executed_at
        trade_plan_id = (
            base.trade_plan_id if base and base.trade_plan_id else execution.trade_plan_id
        )
        this_fee_per_share = execution.fee / execution.quantity

        new_state = PositionState(
            status=PositionStatus.OPEN,
            trade_plan_id=trade_plan_id,
            quantity_open=prior_quantity + execution.quantity,
            avg_entry_price=_weighted_avg_entry(
                prior_quantity, prior_avg_price, execution.quantity, execution.price
            ),
            avg_entry_fee_per_share=_weighted_avg_entry(
                prior_quantity, prior_avg_fee_per_share, execution.quantity, this_fee_per_share
            ),
            cumulative_quantity_bought=prior_bought + execution.quantity,
            cumulative_entry_fees=prior_entry_fees + execution.fee,
            cumulative_exit_fees=prior_exit_fees,
            realized_pnl=prior_realized_pnl,
            opened_at=opened_at,
            closed_at=None,
        )
        return ApplyExecutionResult(new_state=new_state, realized_pnl_impact=None)

    # SELL
    if current is None or current.status not in (
        PositionStatus.OPEN,
        PositionStatus.PARTIALLY_CLOSED,
    ):
        raise ValueError("cannot sell without an open position")
    if execution.quantity > current.quantity_open:
        raise ValueError(
            f"cannot sell {execution.quantity} shares — only "
            f"{current.quantity_open} open (no short-selling in this model)"
        )
    if current.avg_entry_price is None or current.cumulative_quantity_bought <= 0:
        raise ValueError("position has no recorded entry cost basis")

    entry_fee_share = current.avg_entry_fee_per_share * execution.quantity
    realized_pnl_impact = (
        (execution.price - current.avg_entry_price) * execution.quantity
        - entry_fee_share
        - execution.fee
    )

    remaining_quantity = current.quantity_open - execution.quantity
    new_status = (
        PositionStatus.CLOSED if remaining_quantity == 0 else PositionStatus.PARTIALLY_CLOSED
    )

    new_state = replace(
        current,
        status=new_status,
        quantity_open=remaining_quantity,
        cumulative_exit_fees=current.cumulative_exit_fees + execution.fee,
        realized_pnl=current.realized_pnl + realized_pnl_impact,
        closed_at=execution.executed_at if remaining_quantity == 0 else None,
    )
    return ApplyExecutionResult(new_state=new_state, realized_pnl_impact=realized_pnl_impact)
