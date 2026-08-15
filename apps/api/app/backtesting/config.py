"""Canonical backtest configuration.

Bump STRATEGY_VERSION whenever any default/formula below changes, so
historical backtest_runs rows stay traceable to the exact configuration
that produced them (MASTER-PRD §21), mirroring indicator_version/
score_version.

Cost defaults (fee_bps, slippage_bps) are illustrative placeholders, not
verified real IDX broker fees — every BacktestConfig instance records its
actual values used, so results are always traceable to whatever
assumption was in effect, never a hidden default.
"""

from dataclasses import dataclass, field
from datetime import date

from app.db.enums import ExecutionModel, SetupType

STRATEGY_VERSION = "v1"

IDX_LOT_SIZE = 100
DEFAULT_MIN_SCORE = 60.0
DEFAULT_INITIAL_CAPITAL = 100_000_000.0  # IDR, arbitrary illustrative default
DEFAULT_RISK_PER_TRADE_PCT = 0.01
DEFAULT_MAX_CONCURRENT_POSITIONS = 5
DEFAULT_FEE_BPS = 15.0
DEFAULT_SLIPPAGE_BPS = 10.0
DEFAULT_STOP_ATR_MULTIPLIER = 1.5
DEFAULT_TARGET_ATR_MULTIPLIER = 3.0
DEFAULT_MAX_HOLDING_DAYS = 20


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    setup_type: SetupType
    start_date: date
    end_date: date
    min_score: float = DEFAULT_MIN_SCORE
    initial_capital: float = DEFAULT_INITIAL_CAPITAL
    risk_per_trade_pct: float = DEFAULT_RISK_PER_TRADE_PCT
    max_concurrent_positions: int = DEFAULT_MAX_CONCURRENT_POSITIONS
    fee_bps: float = DEFAULT_FEE_BPS
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS
    stop_atr_multiplier: float = DEFAULT_STOP_ATR_MULTIPLIER
    target_atr_multiplier: float = DEFAULT_TARGET_ATR_MULTIPLIER
    max_holding_days: int = DEFAULT_MAX_HOLDING_DAYS
    execution_model: ExecutionModel = field(default=ExecutionModel.NEXT_OPEN)
    strategy_version: str = field(default=STRATEGY_VERSION)
