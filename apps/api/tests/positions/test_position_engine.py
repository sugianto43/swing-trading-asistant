import uuid
from datetime import UTC, datetime

import pytest

from app.db.enums import ExecutionSide, PositionStatus
from app.positions.position_engine import (
    ExecutionInput,
    apply_execution_to_position,
    cancel_planned_state,
    new_planned_state,
)

IID = uuid.uuid4()
T0 = datetime(2024, 1, 1, tzinfo=UTC)
T1 = datetime(2024, 1, 5, tzinfo=UTC)
T2 = datetime(2024, 1, 10, tzinfo=UTC)


def _buy(qty, price, fee=0.0, at=T0, trade_plan_id=None) -> ExecutionInput:
    return ExecutionInput(
        instrument_id=IID,
        side=ExecutionSide.BUY,
        quantity=qty,
        price=price,
        fee=fee,
        executed_at=at,
        trade_plan_id=trade_plan_id,
    )


def _sell(qty, price, fee=0.0, at=T1) -> ExecutionInput:
    return ExecutionInput(
        instrument_id=IID,
        side=ExecutionSide.SELL,
        quantity=qty,
        price=price,
        fee=fee,
        executed_at=at,
    )


def test_buy_from_no_position_opens_position() -> None:
    result = apply_execution_to_position(None, _buy(100, 1000.0, fee=50.0))
    state = result.new_state
    assert state.status == PositionStatus.OPEN
    assert state.quantity_open == 100
    assert state.avg_entry_price == 1000.0
    assert state.cumulative_quantity_bought == 100
    assert state.cumulative_entry_fees == 50.0
    assert state.opened_at == T0
    assert result.realized_pnl_impact is None


def test_buy_from_planned_transitions_to_open() -> None:
    plan_id = uuid.uuid4()
    planned = new_planned_state(plan_id)
    result = apply_execution_to_position(planned, _buy(100, 1000.0))
    assert result.new_state.status == PositionStatus.OPEN
    assert result.new_state.trade_plan_id == plan_id
    assert result.new_state.quantity_open == 100


def test_buy_execution_trade_plan_id_does_not_override_existing_link() -> None:
    plan_id = uuid.uuid4()
    other_plan_id = uuid.uuid4()
    planned = new_planned_state(plan_id)
    opened = apply_execution_to_position(planned, _buy(100, 1000.0)).new_state
    # a second BUY carrying a different trade_plan_id must not silently
    # rewrite which plan this position is attributed to
    added = apply_execution_to_position(
        opened, _buy(50, 1100.0, trade_plan_id=other_plan_id)
    ).new_state
    assert added.trade_plan_id == plan_id


def test_second_buy_recomputes_weighted_average_entry_price() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0)).new_state
    added = apply_execution_to_position(opened, _buy(100, 1200.0)).new_state
    assert added.quantity_open == 200
    # (100*1000 + 100*1200) / 200 = 1100
    assert added.avg_entry_price == pytest.approx(1100.0)
    assert added.cumulative_quantity_bought == 200


def test_sell_reduces_quantity_and_computes_realized_pnl() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0, fee=100.0)).new_state
    result = apply_execution_to_position(opened, _sell(100, 1100.0, fee=50.0))
    # pnl = (1100-1000)*100 - entry_fee_share(100) - exit_fee(50) = 10000-100-50=9850
    assert result.realized_pnl_impact == pytest.approx(9850.0)
    assert result.new_state.status == PositionStatus.CLOSED
    assert result.new_state.quantity_open == 0
    assert result.new_state.closed_at == T1


def test_sell_to_zero_closes_partial_sell_stays_partially_closed() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0)).new_state
    partial = apply_execution_to_position(opened, _sell(40, 1100.0))
    assert partial.new_state.status == PositionStatus.PARTIALLY_CLOSED
    assert partial.new_state.quantity_open == 60
    assert partial.new_state.closed_at is None

    final = apply_execution_to_position(partial.new_state, _sell(60, 1050.0))
    assert final.new_state.status == PositionStatus.CLOSED
    assert final.new_state.quantity_open == 0


def test_sell_avg_entry_price_unaffected_by_partial_sell() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0)).new_state
    partial = apply_execution_to_position(opened, _sell(40, 2000.0)).new_state
    assert partial.avg_entry_price == 1000.0  # cost basis of remaining shares unchanged


def test_sell_exceeding_open_quantity_rejected() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0)).new_state
    with pytest.raises(ValueError, match="cannot sell"):
        apply_execution_to_position(opened, _sell(150, 1000.0))


def test_sell_without_open_position_rejected() -> None:
    with pytest.raises(ValueError, match="cannot sell without an open position"):
        apply_execution_to_position(None, _sell(100, 1000.0))


def test_sell_on_planned_position_rejected() -> None:
    planned = new_planned_state(uuid.uuid4())
    with pytest.raises(ValueError, match="cannot sell without an open position"):
        apply_execution_to_position(planned, _sell(10, 1000.0))


def test_partial_fills_fee_apportionment_across_multiple_sells() -> None:
    """Fee apportionment must fully account for cumulative entry fees
    exactly once across however many partial exits occur — this is the
    core 'partial fills reconciliation' TDD requirement."""
    opened = apply_execution_to_position(None, _buy(100, 1000.0, fee=100.0)).new_state
    # sell half, then the other half, at different prices
    first = apply_execution_to_position(opened, _sell(50, 1100.0, fee=0.0))
    # entry_fee_share = 100 * (50/100) = 50; pnl = (1100-1000)*50 - 50 - 0 = 4950
    assert first.realized_pnl_impact == pytest.approx(4950.0)

    second = apply_execution_to_position(first.new_state, _sell(50, 900.0, fee=0.0))
    # entry_fee_share = 100 * (50/100) = 50; pnl = (900-1000)*50 - 50 - 0 = -5050
    assert second.realized_pnl_impact == pytest.approx(-5050.0)

    # total entry fees (100) fully apportioned exactly once: 50 + 50 = 100
    total_realized = first.realized_pnl_impact + second.realized_pnl_impact
    raw_price_pnl = (1100 - 1000) * 50 + (900 - 1000) * 50
    assert total_realized == pytest.approx(raw_price_pnl - 100.0)
    assert second.new_state.status == PositionStatus.CLOSED


def test_multiple_buys_then_multiple_partial_sells_reconcile() -> None:
    s1 = apply_execution_to_position(None, _buy(60, 1000.0, fee=30.0)).new_state
    s2 = apply_execution_to_position(s1, _buy(40, 1100.0, fee=20.0)).new_state
    assert s2.quantity_open == 100
    assert s2.cumulative_quantity_bought == 100
    assert s2.cumulative_entry_fees == 50.0
    # weighted avg = (60*1000 + 40*1100)/100 = 1040
    assert s2.avg_entry_price == pytest.approx(1040.0)

    r1 = apply_execution_to_position(s2, _sell(30, 1200.0, fee=10.0))
    r2 = apply_execution_to_position(r1.new_state, _sell(70, 1150.0, fee=15.0))
    assert r2.new_state.quantity_open == 0
    assert r2.new_state.status == PositionStatus.CLOSED
    # entry fees fully apportioned: 50*(30/100) + 50*(70/100) = 15+35=50
    entry_fee_share_1 = 50.0 * (30 / 100)
    entry_fee_share_2 = 50.0 * (70 / 100)
    expected_pnl = (
        (1200 - 1040) * 30
        - entry_fee_share_1
        - 10.0
        + (1150 - 1040) * 70
        - entry_fee_share_2
        - 15.0
    )
    assert r2.new_state.realized_pnl == pytest.approx(expected_pnl)


def test_reopening_after_closed_creates_fresh_state_not_reusing_old() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0)).new_state
    closed = apply_execution_to_position(opened, _sell(100, 1200.0)).new_state
    assert closed.status == PositionStatus.CLOSED

    reopened = apply_execution_to_position(closed, _buy(50, 900.0)).new_state
    assert reopened.status == PositionStatus.OPEN
    assert reopened.quantity_open == 50
    assert reopened.avg_entry_price == 900.0  # fresh cost basis, not blended with the old position
    assert reopened.realized_pnl == 0.0  # fresh position, prior realized P&L not carried over


def test_fee_apportionment_fully_reconciles_when_buy_follows_partial_sell() -> None:
    """Regression for the fix-phase HIGH finding: a BUY that re-adds to a
    position AFTER a partial SELL must not cause any entry fee to go
    unapportioned. Previously, apportioning off cumulative_entry_fees /
    cumulative_quantity_bought (both all-time totals) let a later BUY's
    growing denominator retroactively shrink what an earlier SELL's
    fee-share fraction represented, silently losing money from
    realized_pnl. The fix tracks avg_entry_fee_per_share the same
    weighted-average way avg_entry_price already correctly was."""
    opened = apply_execution_to_position(None, _buy(100, 1000.0, fee=10.0)).new_state
    first_sell = apply_execution_to_position(opened, _sell(40, 1100.0, fee=0.0))
    # re-add to the position AFTER the partial sell
    rebought = apply_execution_to_position(
        first_sell.new_state, _buy(50, 1200.0, fee=20.0)
    ).new_state
    final_sell = apply_execution_to_position(rebought, _sell(110, 1200.0, fee=0.0))

    total_fees_paid = 10.0 + 20.0  # both BUY fees
    total_apportioned_entry_fees = (
        # first sell's implied entry-fee share = raw price pnl - realized_pnl_impact
        ((1100.0 - 1000.0) * 40 - first_sell.realized_pnl_impact)
        # final sell's implied entry-fee share, same derivation
        + ((1200.0 - rebought.avg_entry_price) * 110 - final_sell.realized_pnl_impact)
    )
    assert total_apportioned_entry_fees == pytest.approx(total_fees_paid)
    assert final_sell.new_state.quantity_open == 0
    assert final_sell.new_state.status == PositionStatus.CLOSED


def test_avg_entry_fee_per_share_tracks_like_avg_entry_price() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0, fee=100.0)).new_state
    assert opened.avg_entry_fee_per_share == pytest.approx(1.0)  # 100 fee / 100 shares

    added = apply_execution_to_position(opened, _buy(100, 1000.0, fee=50.0)).new_state
    # weighted avg fee/share = (100*1.0 + 100*0.5) / 200 = 0.75
    assert added.avg_entry_fee_per_share == pytest.approx(0.75)

    # unaffected by a SELL, same as avg_entry_price
    partial = apply_execution_to_position(added, _sell(50, 1100.0)).new_state
    assert partial.avg_entry_fee_per_share == pytest.approx(0.75)


def test_new_planned_state_defaults() -> None:
    plan_id = uuid.uuid4()
    state = new_planned_state(plan_id)
    assert state.status == PositionStatus.PLANNED
    assert state.trade_plan_id == plan_id
    assert state.quantity_open == 0


def test_cancel_planned_state() -> None:
    state = new_planned_state(uuid.uuid4())
    cancelled = cancel_planned_state(state)
    assert cancelled.status == PositionStatus.CANCELLED


def test_cancel_non_planned_state_rejected() -> None:
    opened = apply_execution_to_position(None, _buy(100, 1000.0)).new_state
    with pytest.raises(ValueError, match="only a PLANNED position"):
        cancel_planned_state(opened)
