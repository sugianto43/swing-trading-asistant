import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import BacktestStatus, ExecutionModel, ExitReason, SetupType


class BacktestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    strategy_version: str
    setup_type: SetupType
    min_score: float
    start_date: date
    end_date: date
    initial_capital: float
    risk_per_trade_pct: float
    max_concurrent_positions: int
    fee_bps: float
    slippage_bps: float
    stop_atr_multiplier: float
    target_atr_multiplier: float
    max_holding_days: int
    execution_model: ExecutionModel
    indicator_version: str
    score_version: str
    status: BacktestStatus
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


class BacktestMetricsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class BacktestRunDetailOut(BacktestRunOut):
    metrics: BacktestMetricsOut | None


class BacktestTradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    setup_type: SetupType
    signal_date: date
    entry_date: date
    entry_price: float
    stop_price: float
    target_price: float
    exit_date: date | None
    exit_price: float | None
    exit_reason: ExitReason | None
    quantity: int
    fees_paid: float
    slippage_cost: float
    pnl: float | None
    r_multiple: float | None
    holding_days: int | None


class EquityPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_date: date
    equity_value: float
