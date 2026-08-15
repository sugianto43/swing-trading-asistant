"""Read-only performance aggregation over the real execution/position
ledger (MASTER-PRD §11). Distinct from app.backtesting.metrics, which
scores simulated trades — this scores what actually happened. The two
equity-curve-shaped helpers (max_drawdown_pct, sharpe_ratio) are pure
functions of `list[tuple[date, float]]` with no coupling to simulated
trades, so they're reused directly rather than reimplemented.

Deliberately NOT implemented here (documented gap, not a silent one):
- performance by market regime — no market-wide/breadth data source
  exists yet (Phase 9 scope), same gap already documented since Phase 4's
  scanner.
- early-exit / late-entry classification and recurring-mistake pattern
  detection — these require a subjective heuristic the PRD doesn't
  specify; only clearly-defined, non-subjective behavior metrics
  (stop-violation, entry/quantity deviation from plan) are computed.
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtesting.metrics import max_drawdown_pct, sharpe_ratio
from app.db.enums import ExecutionSide, PositionStatus
from app.db.models import Execution, Instrument, Position, PriceBar, ScanCandidate, TradePlan

HOLDING_PERIOD_BUCKETS = [(0, 5), (6, 10), (11, 20), (21, None)]  # inclusive day ranges, in days
SCORE_BUCKETS = [(0, 59.99), (60, 69.99), (70, 79.99), (80, 100)]  # composite_score ranges


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    initial_capital: float
    total_realized_pnl: float
    unrealized_pnl: float
    exposure: float
    closed_position_count: int
    win_rate_pct: float
    avg_win: float | None
    avg_loss: float | None
    expectancy: float | None
    profit_factor: float | None
    max_drawdown_pct: float
    sharpe_ratio: float | None
    equity_curve: list[tuple[date, float]]


@dataclass(frozen=True, slots=True)
class GroupPerformance:
    key: str | None  # None means "no linked trade plan / unknown"
    closed_position_count: int
    total_realized_pnl: float
    win_rate_pct: float


@dataclass(frozen=True, slots=True)
class BehaviorEntry:
    position_id: object
    stop_violated: bool | None  # None when no linked plan / no stop to compare against
    entry_deviation_pct: float | None
    quantity_deviation_pct: float | None


def _closed_positions_with_pnl(session: Session) -> list[Position]:
    return list(
        session.scalars(select(Position).where(Position.status == PositionStatus.CLOSED)).all()
    )


def _win_rate_pct(pnls: list[float]) -> float:
    if not pnls:
        return 0.0
    return sum(1 for p in pnls if p > 0) / len(pnls) * 100


def _avg_win(pnls: list[float]) -> float | None:
    wins = [p for p in pnls if p > 0]
    return statistics.mean(wins) if wins else None


def _avg_loss(pnls: list[float]) -> float | None:
    losses = [p for p in pnls if p < 0]
    return statistics.mean(losses) if losses else None


def _expectancy(pnls: list[float]) -> float | None:
    return statistics.mean(pnls) if pnls else None


def _profit_factor(pnls: list[float]) -> float | None:
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = sum(p for p in pnls if p < 0)
    if gross_loss == 0:
        return None
    return gross_win / abs(gross_loss)


class PerformanceService:
    def __init__(self, session: Session):
        self.session = session

    def equity_curve(self, initial_capital: float = 0.0) -> list[tuple[date, float]]:
        """Cumulative realized P&L over time, one point per SELL
        execution's date (fees are already netted into
        realized_pnl_impact — see position_engine's formula). Does not
        include unrealized/mark-to-market movement — that's reported
        separately in `summary()` since it depends on the caller's
        as-of date, not the historical ledger."""
        sells = self.session.scalars(
            select(Execution)
            .where(Execution.side == ExecutionSide.SELL)
            .order_by(Execution.executed_at)
        ).all()
        curve: list[tuple[date, float]] = []
        running = initial_capital
        for execution in sells:
            running += float(execution.realized_pnl_impact or 0.0)
            curve.append((execution.executed_at.date(), running))
        return curve

    def _unrealized_pnl_and_exposure(self) -> tuple[float, float]:
        open_positions = self.session.scalars(
            select(Position).where(
                Position.status.in_((PositionStatus.OPEN, PositionStatus.PARTIALLY_CLOSED))
            )
        ).all()
        unrealized_pnl = 0.0
        exposure = 0.0
        for position in open_positions:
            cost_basis = position.quantity_open * float(position.avg_entry_price or 0.0)
            exposure += cost_basis
            latest_bar = self.session.scalar(
                select(PriceBar)
                .where(PriceBar.instrument_id == position.instrument_id)
                .order_by(PriceBar.trade_date.desc())
                .limit(1)
            )
            if latest_bar is not None:
                market_value = position.quantity_open * float(latest_bar.close)
                unrealized_pnl += market_value - cost_basis
            # no price data at all for this instrument: unrealized P&L
            # for it is simply omitted (not fabricated as zero-implying
            # "no gain/loss") — exposure still reflects cost basis.
        return unrealized_pnl, exposure

    def summary(self, initial_capital: float = 0.0) -> PerformanceSummary:
        closed = _closed_positions_with_pnl(self.session)
        pnls = [float(p.realized_pnl) for p in closed]
        curve = self.equity_curve(initial_capital)
        # anchor the initial-capital point at the SAME date as the first
        # real data point (never "today") — max_drawdown_pct/sharpe_ratio
        # trust list order as chronological, so an anchor dated after the
        # historical executions it precedes would silently corrupt both.
        full_curve = [(curve[0][0], initial_capital), *curve] if curve else []
        unrealized_pnl, exposure = self._unrealized_pnl_and_exposure()

        return PerformanceSummary(
            initial_capital=initial_capital,
            total_realized_pnl=sum(pnls),
            unrealized_pnl=unrealized_pnl,
            exposure=exposure,
            closed_position_count=len(closed),
            win_rate_pct=_win_rate_pct(pnls),
            avg_win=_avg_win(pnls),
            avg_loss=_avg_loss(pnls),
            expectancy=_expectancy(pnls),
            profit_factor=_profit_factor(pnls),
            max_drawdown_pct=max_drawdown_pct(full_curve) if full_curve else 0.0,
            sharpe_ratio=sharpe_ratio(full_curve) if full_curve else None,
            equity_curve=curve,
        )

    def by_setup(self) -> list[GroupPerformance]:
        closed = _closed_positions_with_pnl(self.session)
        groups: dict[str | None, list[float]] = defaultdict(list)
        for position in closed:
            setup_type = None
            if position.trade_plan_id is not None:
                plan = self.session.scalar(
                    select(TradePlan).where(TradePlan.id == position.trade_plan_id)
                )
                setup_type = plan.setup_type.value if plan else None
            groups[setup_type].append(float(position.realized_pnl))
        return [
            GroupPerformance(
                key=key,
                closed_position_count=len(pnls),
                total_realized_pnl=sum(pnls),
                win_rate_pct=_win_rate_pct(pnls),
            )
            for key, pnls in groups.items()
        ]

    def by_sector(self) -> list[GroupPerformance]:
        closed = _closed_positions_with_pnl(self.session)
        groups: dict[str | None, list[float]] = defaultdict(list)
        for position in closed:
            instrument = self.session.scalar(
                select(Instrument).where(Instrument.id == position.instrument_id)
            )
            sector = instrument.sector if instrument else None
            groups[sector].append(float(position.realized_pnl))
        return [
            GroupPerformance(
                key=key,
                closed_position_count=len(pnls),
                total_realized_pnl=sum(pnls),
                win_rate_pct=_win_rate_pct(pnls),
            )
            for key, pnls in groups.items()
        ]

    def by_holding_period(self) -> list[GroupPerformance]:
        closed = _closed_positions_with_pnl(self.session)
        groups: dict[str | None, list[float]] = defaultdict(list)
        for position in closed:
            if position.opened_at is None or position.closed_at is None:
                groups[None].append(float(position.realized_pnl))
                continue
            days = (position.closed_at - position.opened_at).days
            bucket_key = None
            for low, high in HOLDING_PERIOD_BUCKETS:
                if days >= low and (high is None or days <= high):
                    bucket_key = f"{low}-{high}d" if high is not None else f"{low}+d"
                    break
            groups[bucket_key].append(float(position.realized_pnl))
        return [
            GroupPerformance(
                key=key,
                closed_position_count=len(pnls),
                total_realized_pnl=sum(pnls),
                win_rate_pct=_win_rate_pct(pnls),
            )
            for key, pnls in groups.items()
        ]

    def by_score_bucket(self) -> list[GroupPerformance]:
        closed = _closed_positions_with_pnl(self.session)
        groups: dict[str | None, list[float]] = defaultdict(list)
        for position in closed:
            score = None
            if position.trade_plan_id is not None:
                plan = self.session.scalar(
                    select(TradePlan).where(TradePlan.id == position.trade_plan_id)
                )
                if plan is not None and plan.scan_candidate_id is not None:
                    candidate = self.session.scalar(
                        select(ScanCandidate).where(ScanCandidate.id == plan.scan_candidate_id)
                    )
                    if candidate is not None:
                        score = float(candidate.composite_score)
            bucket_key = None
            if score is not None:
                for low, high in SCORE_BUCKETS:
                    if low <= score <= high:
                        bucket_key = f"{low:.0f}-{high:.0f}"
                        break
            groups[bucket_key].append(float(position.realized_pnl))
        return [
            GroupPerformance(
                key=key,
                closed_position_count=len(pnls),
                total_realized_pnl=sum(pnls),
                win_rate_pct=_win_rate_pct(pnls),
            )
            for key, pnls in groups.items()
        ]

    def behavior(self) -> list[BehaviorEntry]:
        closed = _closed_positions_with_pnl(self.session)
        entries: list[BehaviorEntry] = []
        for position in closed:
            if position.trade_plan_id is None:
                entries.append(
                    BehaviorEntry(
                        position_id=position.id,
                        stop_violated=None,
                        entry_deviation_pct=None,
                        quantity_deviation_pct=None,
                    )
                )
                continue
            plan = self.session.scalar(
                select(TradePlan).where(TradePlan.id == position.trade_plan_id)
            )
            executions = list(
                self.session.scalars(
                    select(Execution)
                    .where(Execution.position_id == position.id)
                    .order_by(Execution.executed_at)
                ).all()
            )
            buys = [e for e in executions if e.side == ExecutionSide.BUY]
            sells = [e for e in executions if e.side == ExecutionSide.SELL]

            stop_violated = None
            if plan is not None and plan.stop_price is not None and sells:
                last_sell = sells[-1]
                stop_violated = float(last_sell.price) < float(plan.stop_price)

            entry_deviation_pct = None
            if plan is not None and plan.entry_price is not None and buys:
                first_buy_price = float(buys[0].price)
                planned_entry = float(plan.entry_price)
                if planned_entry > 0:
                    entry_deviation_pct = (first_buy_price - planned_entry) / planned_entry * 100

            quantity_deviation_pct = None
            if plan is not None and plan.quantity:
                total_bought = sum(e.quantity for e in buys)
                quantity_deviation_pct = (total_bought - plan.quantity) / plan.quantity * 100

            entries.append(
                BehaviorEntry(
                    position_id=position.id,
                    stop_violated=stop_violated,
                    entry_deviation_pct=entry_deviation_pct,
                    quantity_deviation_pct=quantity_deviation_pct,
                )
            )
        return entries
