import bisect
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from app.backtesting.config import BacktestConfig
from app.backtesting.costs import apply_slippage_to_price, compute_fee
from app.backtesting.sizing import compute_position_size
from app.db.enums import ExitReason, SetupType
from app.scanner.context import ScanPoint


@dataclass(frozen=True, slots=True)
class EntrySignal:
    """Decoupled from the ORM ScanCandidate row, so the simulator stays a
    pure function testable without a database."""

    instrument_id: uuid.UUID
    setup_type: SetupType
    signal_date: date
    score: float


@dataclass(frozen=True, slots=True)
class TradeResult:
    instrument_id: uuid.UUID
    setup_type: SetupType
    signal_date: date
    entry_date: date
    entry_price: float
    stop_price: float
    target_price: float
    exit_date: date
    exit_price: float
    exit_reason: ExitReason
    quantity: int
    fees_paid: float
    slippage_cost: float
    pnl: float
    r_multiple: float
    holding_days: int


@dataclass(slots=True)
class _OpenPosition:
    instrument_id: uuid.UUID
    setup_type: SetupType
    signal_date: date
    entry_date: date
    entry_price: float
    raw_entry_price: float
    stop_price: float
    target_price: float
    quantity: int
    entry_fee: float
    entry_slippage_cost: float
    days_held: int = 0


@dataclass(frozen=True, slots=True)
class SimulationResult:
    trades: list[TradeResult]
    equity_curve: list[tuple[date, float]]


def _close_trade(
    pos: _OpenPosition,
    exit_date: date,
    raw_exit_price: float,
    exit_reason: ExitReason,
    config: BacktestConfig,
) -> tuple[TradeResult, float]:
    """Returns (trade_result, cash_proceeds)."""
    is_stop_or_target_fill = exit_reason in (ExitReason.STOP, ExitReason.TARGET)
    # a stop/target fill is assumed to execute exactly at that price level
    # (no additional slippage beyond what's already conservative about
    # same-bar conflicts); a time/end-of-backtest exit is a real order at
    # the close, so slippage applies there too.
    exit_price = (
        raw_exit_price
        if is_stop_or_target_fill
        else apply_slippage_to_price(raw_exit_price, config.slippage_bps, is_buy=False)
    )
    exit_slippage_cost = (raw_exit_price - exit_price) * pos.quantity

    notional = exit_price * pos.quantity
    exit_fee = compute_fee(notional, config.fee_bps)

    fees_paid = pos.entry_fee + exit_fee
    slippage_cost = pos.entry_slippage_cost + exit_slippage_cost
    pnl = (exit_price - pos.entry_price) * pos.quantity - fees_paid

    stop_distance = pos.entry_price - pos.stop_price
    r_multiple = (exit_price - pos.entry_price) / stop_distance if stop_distance > 0 else 0.0

    trade = TradeResult(
        instrument_id=pos.instrument_id,
        setup_type=pos.setup_type,
        signal_date=pos.signal_date,
        entry_date=pos.entry_date,
        entry_price=pos.entry_price,
        stop_price=pos.stop_price,
        target_price=pos.target_price,
        exit_date=exit_date,
        exit_price=exit_price,
        exit_reason=exit_reason,
        quantity=pos.quantity,
        fees_paid=fees_paid,
        slippage_cost=slippage_cost,
        pnl=pnl,
        r_multiple=r_multiple,
        holding_days=pos.days_held,
    )
    cash_proceeds = notional - exit_fee
    return trade, cash_proceeds


def _try_open_position(
    signal: EntrySignal,
    entry_point: ScanPoint,
    signal_day_atr: float | None,
    equity: float,
    config: BacktestConfig,
) -> tuple[_OpenPosition, float] | None:
    """Returns (position, cash_committed) or None if the signal can't be
    filled (missing signal-day ATR, non-positive stop, or sizing to zero
    shares).

    Stop/target are derived from the SIGNAL day's ATR, not the entry day's
    — the entry fills at the entry day's open, before that day's own
    high/low (and therefore its own ATR) exist. Using the entry day's ATR
    would size every trade's risk off information not yet available at
    the moment of the trade (MASTER-PRD §8 no-look-ahead). The signal
    day's ATR was already fully known when the scan ran after that day's
    close, so it's the correct, already-knowable basis.
    """
    if signal_day_atr is None or signal_day_atr <= 0:
        return None

    raw_entry_price = entry_point.open
    entry_price = apply_slippage_to_price(raw_entry_price, config.slippage_bps, is_buy=True)
    stop_price = entry_price - config.stop_atr_multiplier * signal_day_atr
    target_price = entry_price + config.target_atr_multiplier * signal_day_atr
    if stop_price <= 0:
        return None

    quantity = compute_position_size(equity, entry_price, stop_price, config.risk_per_trade_pct)
    if quantity <= 0:
        return None

    notional = entry_price * quantity
    entry_fee = compute_fee(notional, config.fee_bps)
    entry_slippage_cost = (entry_price - raw_entry_price) * quantity
    cash_committed = notional + entry_fee

    position = _OpenPosition(
        instrument_id=signal.instrument_id,
        setup_type=signal.setup_type,
        signal_date=signal.signal_date,
        entry_date=entry_point.trade_date,
        entry_price=entry_price,
        raw_entry_price=raw_entry_price,
        stop_price=stop_price,
        target_price=target_price,
        quantity=quantity,
        entry_fee=entry_fee,
        entry_slippage_cost=entry_slippage_cost,
    )
    return position, cash_committed


def _build_fill_schedule(
    config: BacktestConfig,
    points_by_instrument: dict[uuid.UUID, list[ScanPoint]],
    signals: list[EntrySignal],
) -> dict[date, list[EntrySignal]]:
    """For each signal, find that instrument's OWN first available
    trading date strictly after signal_date (within the backtest window)
    and schedule the fill there — instrument-local, so one symbol's data
    gap can never depend on whether some other, unrelated symbol happens
    to have data that day. A signal whose instrument has no data at all
    after signal_date within the window never fills (this is not the
    same failure mode as before: it is now deterministic and based only
    on that instrument's own data)."""
    dates_by_instrument: dict[uuid.UUID, list[date]] = {
        instrument_id: sorted(
            {
                point.trade_date
                for point in points
                if config.start_date <= point.trade_date <= config.end_date
            }
        )
        for instrument_id, points in points_by_instrument.items()
    }

    schedule: dict[date, list[EntrySignal]] = {}
    for signal in signals:
        if signal.setup_type != config.setup_type:
            continue
        dates = dates_by_instrument.get(signal.instrument_id, [])
        idx = bisect.bisect_right(dates, signal.signal_date)
        if idx >= len(dates):
            continue  # no data at all after the signal within the window
        fill_date = dates[idx]
        schedule.setdefault(fill_date, []).append(signal)

    # deterministic priority when multiple signals compete for the same
    # fill date (e.g. a max_concurrent_positions cap binds): highest
    # score first, instrument id as a stable tiebreaker.
    for pending in schedule.values():
        pending.sort(key=lambda s: (-s.score, str(s.instrument_id)))

    return schedule


def run_simulation(
    config: BacktestConfig,
    points_by_instrument: dict[uuid.UUID, list[ScanPoint]],
    signals: list[EntrySignal],
    is_eligible: Callable[[uuid.UUID, date], bool],
) -> SimulationResult:
    """Day-by-day event simulation. No look-ahead by construction: on
    trading day T, exits are decided using only day T's ScanPoint (its
    own low/high/close); new entries fill at the instrument's own next
    available trading day strictly after its signal date (see
    _build_fill_schedule) — a signal can never be acted on the same day
    it fired, and one instrument's data gap never depends on another
    instrument's data availability.
    """
    point_index: dict[tuple[uuid.UUID, date], ScanPoint] = {
        (instrument_id, point.trade_date): point
        for instrument_id, points in points_by_instrument.items()
        for point in points
    }
    fill_schedule = _build_fill_schedule(config, points_by_instrument, signals)

    all_dates = sorted(
        {
            point.trade_date
            for points in points_by_instrument.values()
            for point in points
            if config.start_date <= point.trade_date <= config.end_date
        }
    )

    cash = config.initial_capital
    open_positions: dict[uuid.UUID, _OpenPosition] = {}
    trades: list[TradeResult] = []
    equity_curve: list[tuple[date, float]] = []

    for current_date in all_dates:
        # 1. exits, using only today's data
        for instrument_id in list(open_positions):
            pos = open_positions[instrument_id]
            point = point_index.get((instrument_id, current_date))
            if point is None:
                continue  # no data today (e.g. suspended) — position stays open
            pos.days_held += 1

            exit_reason: ExitReason | None = None
            raw_exit_price = 0.0
            # same-bar stop+target conflict resolved conservatively: stop wins
            if point.low <= pos.stop_price:
                exit_reason, raw_exit_price = ExitReason.STOP, pos.stop_price
            elif point.high >= pos.target_price:
                exit_reason, raw_exit_price = ExitReason.TARGET, pos.target_price
            elif pos.days_held >= config.max_holding_days:
                exit_reason, raw_exit_price = ExitReason.TIME, point.close

            if exit_reason is not None:
                trade, cash_proceeds = _close_trade(
                    pos, current_date, raw_exit_price, exit_reason, config
                )
                cash += cash_proceeds
                trades.append(trade)
                del open_positions[instrument_id]

        # 2. entries: signals scheduled to fill exactly today
        for signal in fill_schedule.get(current_date, []):
            instrument_id = signal.instrument_id
            if instrument_id in open_positions:
                continue
            if len(open_positions) >= config.max_concurrent_positions:
                continue
            if not is_eligible(instrument_id, current_date):
                continue
            entry_point = point_index.get((instrument_id, current_date))
            if entry_point is None:
                continue
            signal_point = point_index.get((instrument_id, signal.signal_date))
            signal_day_atr = signal_point.atr_14 if signal_point is not None else None

            # equity for sizing uses cash + OTHER open positions at cost
            # basis (their entry price), never today's not-yet-known
            # close — sizing a new trade off same-day information for a
            # different position would be its own small look-ahead leak.
            current_equity = cash + sum(
                p.quantity * p.entry_price
                for pid, p in open_positions.items()
                if pid != instrument_id
            )
            opened = _try_open_position(signal, entry_point, signal_day_atr, current_equity, config)
            if opened is None:
                continue
            position, cash_committed = opened
            if cash_committed > cash:
                continue
            cash -= cash_committed
            open_positions[instrument_id] = position

        # 3. mark-to-market equity for today
        market_value = sum(
            point_index[(pid, current_date)].close * pos.quantity
            for pid, pos in open_positions.items()
            if (pid, current_date) in point_index
        )
        equity_curve.append((current_date, cash + market_value))

    # force-close anything still open at the end of the backtest window
    if all_dates:
        final_date = all_dates[-1]
        for instrument_id in list(open_positions):
            pos = open_positions[instrument_id]
            point = point_index.get((instrument_id, final_date))
            exit_price = point.close if point is not None else pos.entry_price
            trade, cash_proceeds = _close_trade(
                pos, final_date, exit_price, ExitReason.END_OF_BACKTEST, config
            )
            cash += cash_proceeds
            trades.append(trade)
        if open_positions and equity_curve:
            equity_curve[-1] = (final_date, cash)

    return SimulationResult(trades=trades, equity_curve=equity_curve)
