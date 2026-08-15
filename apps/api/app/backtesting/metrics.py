"""Performance metrics (MASTER-PRD FR-012). Every formula documented
explicitly — no library defaults, no hidden assumptions.
"""

import math
import statistics
from dataclasses import dataclass
from datetime import date

from app.backtesting.simulator import TradeResult

TRADING_DAYS_PER_YEAR = 252
MIN_DAYS_FOR_CAGR = 30  # shorter windows produce unstable/misleading annualized figures
RISK_FREE_RATE = 0.0  # simplifying assumption, documented rather than fabricated


@dataclass(frozen=True, slots=True)
class BacktestMetricsResult:
    total_return_pct: float
    cagr_pct: float | None
    win_rate_pct: float
    avg_win: float | None
    avg_loss: float | None
    expectancy: float | None
    profit_factor: float | None
    max_drawdown_pct: float
    sharpe_ratio: float | None
    trade_count: int
    avg_holding_days: float | None
    r_distribution: list[float]


def total_return_pct(initial_capital: float, final_equity: float) -> float:
    if initial_capital <= 0:
        return 0.0
    return (final_equity - initial_capital) / initial_capital * 100


def cagr_pct(
    initial_capital: float, final_equity: float, start_date: date, end_date: date
) -> float | None:
    days = (end_date - start_date).days
    if days < MIN_DAYS_FOR_CAGR or initial_capital <= 0 or final_equity <= 0:
        return None
    years = days / 365.25
    return (float((final_equity / initial_capital) ** (1 / years)) - 1) * 100


def win_rate_pct(trades: list[TradeResult]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.pnl > 0)
    return wins / len(trades) * 100


def avg_win(trades: list[TradeResult]) -> float | None:
    wins = [t.pnl for t in trades if t.pnl > 0]
    return statistics.mean(wins) if wins else None


def avg_loss(trades: list[TradeResult]) -> float | None:
    losses = [t.pnl for t in trades if t.pnl < 0]
    return statistics.mean(losses) if losses else None


def expectancy(trades: list[TradeResult]) -> float | None:
    if not trades:
        return None
    return statistics.mean(t.pnl for t in trades)


def profit_factor(trades: list[TradeResult]) -> float | None:
    gross_win = sum(t.pnl for t in trades if t.pnl > 0)
    gross_loss = sum(t.pnl for t in trades if t.pnl < 0)
    if gross_loss == 0:
        return None  # undefined (no losing trades) rather than a fabricated infinity
    return gross_win / abs(gross_loss)


def max_drawdown_pct(equity_curve: list[tuple[date, float]]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0][1]
    max_dd = 0.0
    for _, equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd * 100


def sharpe_ratio(equity_curve: list[tuple[date, float]]) -> float | None:
    """Daily returns, annualized by sqrt(252), risk-free rate assumed 0%
    (RISK_FREE_RATE) — a documented simplification, not a market fact."""
    if len(equity_curve) < 3:
        return None
    daily_returns = [
        (equity_curve[i][1] - equity_curve[i - 1][1]) / equity_curve[i - 1][1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1][1] > 0
    ]
    if len(daily_returns) < 2:
        return None
    mean_return = statistics.mean(daily_returns) - RISK_FREE_RATE
    stdev_return = statistics.stdev(daily_returns)
    if stdev_return == 0:
        return None
    return (mean_return / stdev_return) * math.sqrt(TRADING_DAYS_PER_YEAR)


def avg_holding_days(trades: list[TradeResult]) -> float | None:
    if not trades:
        return None
    return statistics.mean(t.holding_days for t in trades)


def r_distribution(trades: list[TradeResult]) -> list[float]:
    return [t.r_multiple for t in trades]


def compute_metrics(
    trades: list[TradeResult],
    equity_curve: list[tuple[date, float]],
    initial_capital: float,
    start_date: date,
    end_date: date,
) -> BacktestMetricsResult:
    final_equity = equity_curve[-1][1] if equity_curve else initial_capital
    return BacktestMetricsResult(
        total_return_pct=total_return_pct(initial_capital, final_equity),
        cagr_pct=cagr_pct(initial_capital, final_equity, start_date, end_date),
        win_rate_pct=win_rate_pct(trades),
        avg_win=avg_win(trades),
        avg_loss=avg_loss(trades),
        expectancy=expectancy(trades),
        profit_factor=profit_factor(trades),
        max_drawdown_pct=max_drawdown_pct(equity_curve),
        sharpe_ratio=sharpe_ratio(equity_curve),
        trade_count=len(trades),
        avg_holding_days=avg_holding_days(trades),
        r_distribution=r_distribution(trades),
    )
