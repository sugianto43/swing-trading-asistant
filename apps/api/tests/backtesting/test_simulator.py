import uuid
from datetime import date, timedelta

import pytest

from app.backtesting.config import BacktestConfig
from app.backtesting.simulator import EntrySignal, run_simulation
from app.db.enums import ExitReason, SetupType
from tests.scanner.helpers import point

ALWAYS_ELIGIBLE = lambda instrument_id, as_of: True  # noqa: E731


def _flat_series(
    iid,
    n: int,
    price: float = 1000.0,
    atr: float = 20.0,
    start_date: date = date(2024, 1, 1),
    high_mult: float = 1.0,
    low_mult: float = 1.0,
):
    return {
        iid: [
            point(
                i,
                price,
                start_date=start_date,
                high=price * high_mult,
                low=price * low_mult,
                atr_14=atr,
            )
            for i in range(n)
        ]
    }


def test_simulation_no_signals_no_trades() -> None:
    iid = uuid.uuid4()
    points = _flat_series(iid, 10)
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=date(2024, 1, 1), end_date=date(2024, 1, 10)
    )
    result = run_simulation(config, points, [], ALWAYS_ELIGIBLE)
    assert result.trades == []
    assert len(result.equity_curve) == 10


def test_entry_fills_at_next_day_open_never_signal_day() -> None:
    iid = uuid.uuid4()
    points = _flat_series(iid, 15)
    signal_date = date(2024, 1, 1) + timedelta(days=3)
    signals = [EntrySignal(iid, SetupType.BREAKOUT, signal_date, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=date(2024, 1, 1), end_date=date(2024, 1, 15)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    assert result.trades[0].entry_date == signal_date + timedelta(days=1)
    assert result.trades[0].signal_date == signal_date


def test_signal_on_final_day_never_fills() -> None:
    # a signal dated the last day in the series has no "tomorrow" to fill at
    iid = uuid.uuid4()
    points = _flat_series(iid, 5)
    signal_date = date(2024, 1, 1) + timedelta(days=4)
    signals = [EntrySignal(iid, SetupType.BREAKOUT, signal_date, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=date(2024, 1, 1), end_date=date(2024, 1, 5)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert result.trades == []


def test_target_exit() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    pts = [point(0, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0)]
    pts.append(point(1, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0))
    # day 2: price gaps up, high touches target (entry + 3*20=60 above entry)
    pts.append(point(2, 1065.0, start_date=start, high=1070.0, low=1060.0, atr_14=20.0))
    points = {iid: pts}
    signals = [EntrySignal(iid, SetupType.BREAKOUT, start, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=2)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == ExitReason.TARGET


def test_stop_exit() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    pts = [point(0, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0)]
    pts.append(point(1, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0))
    # day 2: price drops, low touches stop (entry - 1.5*20=30 below)
    pts.append(point(2, 970.0, start_date=start, high=1000.0, low=965.0, atr_14=20.0))
    points = {iid: pts}
    signals = [EntrySignal(iid, SetupType.BREAKOUT, start, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=2)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == ExitReason.STOP


def test_same_bar_stop_and_target_conflict_stop_wins() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    pts = [point(0, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0)]
    pts.append(point(1, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0))
    # day 2: huge range bar that touches BOTH stop and target
    pts.append(point(2, 1000.0, start_date=start, high=1200.0, low=900.0, atr_14=20.0))
    points = {iid: pts}
    signals = [EntrySignal(iid, SetupType.BREAKOUT, start, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=2)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == ExitReason.STOP  # documented conservative rule


def test_time_exit_after_max_holding_days() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    # flat, never hits stop or target, runs past max_holding_days
    points = _flat_series(iid, 30, price=1000.0, atr=20.0, start_date=start)
    signals = [EntrySignal(iid, SetupType.BREAKOUT, start, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=start,
        end_date=start + timedelta(days=29),
        max_holding_days=5,
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == ExitReason.TIME
    assert result.trades[0].holding_days == 5


def test_end_of_backtest_force_closes_open_position() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    points = _flat_series(iid, 5, price=1000.0, atr=20.0, start_date=start)
    signals = [EntrySignal(iid, SetupType.BREAKOUT, start + timedelta(days=1), 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=4)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == ExitReason.END_OF_BACKTEST


def test_survivorship_ineligible_instrument_never_enters() -> None:
    iid = uuid.uuid4()
    points = _flat_series(iid, 10)
    signals = [EntrySignal(iid, SetupType.BREAKOUT, date(2024, 1, 1), 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=date(2024, 1, 1), end_date=date(2024, 1, 10)
    )
    result = run_simulation(config, points, signals, lambda i, d: False)
    assert result.trades == []


def test_max_concurrent_positions_cap() -> None:
    iid1, iid2, iid3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    start = date(2024, 1, 1)
    points = {}
    for iid in (iid1, iid2, iid3):
        points.update(_flat_series(iid, 10, start_date=start))
    signals = [
        EntrySignal(iid1, SetupType.BREAKOUT, start, 80.0),
        EntrySignal(iid2, SetupType.BREAKOUT, start, 80.0),
        EntrySignal(iid3, SetupType.BREAKOUT, start, 80.0),
    ]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=start,
        end_date=start + timedelta(days=9),
        max_concurrent_positions=2,
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    # at most 2 should have ever opened (3rd signal has no room)
    entered_instruments = {t.instrument_id for t in result.trades}
    assert len(entered_instruments) <= 2


def test_missing_atr_signal_is_skipped_not_fabricated() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    pts = [
        point(i, 1000.0, start_date=start, atr_14=None)  # no ATR anywhere
        for i in range(5)
    ]
    points = {iid: pts}
    signals = [EntrySignal(iid, SetupType.BREAKOUT, start, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=4)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert result.trades == []


def test_reproducibility_identical_input_identical_output() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    points = _flat_series(iid, 20, start_date=start)
    signals = [EntrySignal(iid, SetupType.BREAKOUT, start + timedelta(days=2), 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=19)
    )
    first = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    second = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert first.trades == second.trades
    assert first.equity_curve == second.equity_curve


def test_no_look_ahead_future_mutation() -> None:
    """The core adversarial test: a trade that fully closes within the
    first N days, and the equity curve up through day N, must be
    identical whether or not later (mutated) data exists beyond N."""
    iid = uuid.uuid4()
    start = date(2024, 1, 1)

    def _series(n: int, mutate_from_day: int | None) -> dict:
        pts = []
        for i in range(n):
            if mutate_from_day is not None and i >= mutate_from_day:
                pts.append(point(i, 999999.0, start_date=start, high=1999999.0, low=999999.0))
            elif i == 3:
                # day 3: gap up through target (entry+3*20=60 above entry~1000)
                pts.append(point(i, 1065.0, start_date=start, high=1070.0, low=1060.0, atr_14=20.0))
            else:
                pts.append(point(i, 1000.0, start_date=start, high=1000.0, low=1000.0, atr_14=20.0))
        return {iid: pts}

    signals = [EntrySignal(iid, SetupType.BREAKOUT, start + timedelta(days=1), 80.0)]

    baseline_points = _series(8, mutate_from_day=None)
    baseline_config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=7)
    )
    baseline = run_simulation(baseline_config, baseline_points, signals, ALWAYS_ELIGIBLE)

    extended_points = _series(15, mutate_from_day=8)  # days 8-14 corrupted
    extended_config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=14)
    )
    extended = run_simulation(extended_config, extended_points, signals, ALWAYS_ELIGIBLE)

    # the trade closed on day 3 (well before the mutation point) — identical either way
    assert len(baseline.trades) == 1
    closed_trade = next(t for t in extended.trades if t.exit_reason == ExitReason.TARGET)
    assert closed_trade == baseline.trades[0]

    # equity curve prefix through day 7 must match exactly regardless of
    # what garbage exists on days 8-14
    baseline_curve = baseline.equity_curve
    extended_prefix = extended.equity_curve[: len(baseline_curve)]
    assert extended_prefix == baseline_curve


def test_stop_target_use_signal_day_atr_not_entry_day_atr() -> None:
    """Regression for the CRITICAL review finding: stop/target must be
    derived from the SIGNAL day's ATR (already known when the scan ran),
    never the entry day's own ATR (not yet knowable at that day's open,
    since it depends on that day's own high/low)."""
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    signal_date = start  # ATR on this day = 20.0
    # entry day (start + 1) has ATR on this day = 200.0 (wildly different)
    pts = [
        point(0, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0),
        point(1, 1000.0, start_date=start, high=1000, low=1000, atr_14=200.0),
        point(2, 1000.0, start_date=start, high=1000, low=1000, atr_14=200.0),
    ]
    points = {iid: pts}
    signals = [EntrySignal(iid, SetupType.BREAKOUT, signal_date, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=start,
        end_date=start + timedelta(days=2),
        stop_atr_multiplier=1.5,
        target_atr_multiplier=3.0,
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    trade = result.trades[0]
    # if the entry day's ATR (200.0) were wrongly used, stop would be
    # ~1000 - 1.5*200 = 700; with the correct signal-day ATR (20.0),
    # stop should be close to 1000 - 1.5*20 = 970
    assert trade.entry_price - trade.stop_price == pytest.approx(1.5 * 20.0, rel=0.01)
    assert trade.target_price - trade.entry_price == pytest.approx(3.0 * 20.0, rel=0.01)


def test_entry_fill_is_instrument_local_not_masked_by_other_symbols() -> None:
    """Regression for the HIGH review finding: instrument A's data gap
    must not depend on whether some unrelated instrument B has data that
    day. Previously, B's presence in the global date union caused A's
    signal to be silently and permanently lost."""
    iid_a, iid_b = uuid.uuid4(), uuid.uuid4()
    start = date(2024, 1, 1)
    # A has a gap on day 2 (the day its signal should naturally fill)
    points_a = [
        point(i, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0)
        for i in range(10)
        if i != 2
    ]
    # B trades every day, keeping day 2 in the global date union
    points_b = [
        point(i, 500.0, start_date=start, high=500, low=500, atr_14=10.0) for i in range(10)
    ]
    points = {iid_a: points_a, iid_b: points_b}
    signals = [EntrySignal(iid_a, SetupType.BREAKOUT, start + timedelta(days=1), 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=9)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    a_trades = [t for t in result.trades if t.instrument_id == iid_a]
    assert len(a_trades) == 1
    # fills at A's own next available day (day 3), not lost
    assert a_trades[0].entry_date == start + timedelta(days=3)


def test_signal_priority_is_deterministic_by_score_when_slots_are_limited() -> None:
    iid_low, iid_high = uuid.uuid4(), uuid.uuid4()
    start = date(2024, 1, 1)
    points = {}
    points.update(_flat_series(iid_low, 10, start_date=start))
    points.update(_flat_series(iid_high, 10, start_date=start))
    signals = [
        EntrySignal(iid_low, SetupType.BREAKOUT, start, score=50.0),
        EntrySignal(iid_high, SetupType.BREAKOUT, start, score=95.0),
    ]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=start,
        end_date=start + timedelta(days=9),
        max_concurrent_positions=1,
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1
    assert result.trades[0].instrument_id == iid_high  # higher score wins the single slot


def test_sizing_uses_cost_basis_not_same_day_close_for_other_positions() -> None:
    """Regression for the MEDIUM review finding: sizing a new entry must
    not value already-open positions using the current day's not-yet-known
    close."""
    iid_open, iid_new = uuid.uuid4(), uuid.uuid4()
    start = date(2024, 1, 1)
    # iid_open: entered earlier at 1000, and on the new-entry day its
    # close suddenly spikes to 100000 — if sizing used same-day close for
    # this open position, the new entry's size would be wildly different
    # than if it correctly used the 1000 cost basis.
    points_open = [
        point(0, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0),
        point(1, 1000.0, start_date=start, high=1000, low=1000, atr_14=20.0),
        point(2, 100_000.0, start_date=start, high=100_000, low=100_000, atr_14=20.0),
    ]
    points_new = [
        point(i, 500.0, start_date=start, high=500, low=500, atr_14=10.0) for i in range(3)
    ]
    points = {iid_open: points_open, iid_new: points_new}
    signals = [
        EntrySignal(iid_open, SetupType.BREAKOUT, start, 90.0),
        EntrySignal(iid_new, SetupType.BREAKOUT, start + timedelta(days=1), 90.0),
    ]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT,
        start_date=start,
        end_date=start + timedelta(days=2),
        max_concurrent_positions=5,
        risk_per_trade_pct=0.01,
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    new_trade = next(t for t in result.trades if t.instrument_id == iid_new)
    # expected size using cost-basis equity (unaffected by iid_open's
    # same-day price spike): risk_amount = initial_capital*0.01 fixed
    # regardless of iid_open's mark-to-market swing
    from app.backtesting.sizing import compute_position_size

    expected_qty = compute_position_size(
        equity=config.initial_capital,  # cash after iid_open's entry + open cost basis
        entry_price=new_trade.entry_price,
        stop_price=new_trade.stop_price,
        risk_per_trade_pct=config.risk_per_trade_pct,
    )
    # exact equity denominator is cash + open positions at cost basis, not
    # a fixed value — the key property under test is that it does NOT
    # reflect iid_open's 100,000 same-day close. We assert indirectly:
    # quantity must be modest (sane), not blown up by a 100x phantom gain.
    assert new_trade.quantity <= expected_qty * 2


def test_missing_day_gap_keeps_position_open_not_forced_exit() -> None:
    iid = uuid.uuid4()
    start = date(2024, 1, 1)
    full = _flat_series(iid, 10, start_date=start)[iid]
    entry_signal_date = start + timedelta(days=1)
    # remove day 3 and 4 entirely (simulate a data gap while position is open)
    gapped = [
        p
        for p in full
        if p.trade_date not in (start + timedelta(days=3), start + timedelta(days=4))
    ]
    points = {iid: gapped}
    signals = [EntrySignal(iid, SetupType.BREAKOUT, entry_signal_date, 80.0)]
    config = BacktestConfig(
        setup_type=SetupType.BREAKOUT, start_date=start, end_date=start + timedelta(days=9)
    )
    result = run_simulation(config, points, signals, ALWAYS_ELIGIBLE)
    assert len(result.trades) == 1  # survives the gap, force-closed at end
    assert result.trades[0].exit_reason == ExitReason.END_OF_BACKTEST
