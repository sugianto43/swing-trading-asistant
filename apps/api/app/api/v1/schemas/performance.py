from datetime import date

from pydantic import BaseModel


class PerformanceSummaryOut(BaseModel):
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


class GroupPerformanceOut(BaseModel):
    key: str | None
    closed_position_count: int
    total_realized_pnl: float
    win_rate_pct: float


class BehaviorEntryOut(BaseModel):
    position_id: str
    stop_violated: bool | None
    entry_deviation_pct: float | None
    quantity_deviation_pct: float | None
