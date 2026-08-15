"""Canonical risk-engine configuration.

Bump RISK_VERSION whenever any default/formula below changes, so
historical trade_plans rows stay traceable to the exact configuration
that produced them (MASTER-PRD §21), mirroring indicator_version/
score_version/strategy_version.

These limits are configurable only via code/deploy-time values (this
dataclass), never through any API surface an AI or end user could call at
runtime — that satisfies "AI cannot change these limits" (MASTER-PRD
FR-010) by construction rather than by an access-control check.

Cost defaults (fee_bps, slippage_bps) mirror app/backtesting/config.py's
illustrative placeholders, not verified real IDX broker fees.
"""

from dataclasses import dataclass

from app.backtesting.config import IDX_LOT_SIZE

RISK_VERSION = "v1"

DEFAULT_MAX_PORTFOLIO_EXPOSURE_PCT = 0.80
DEFAULT_MAX_POSITION_ALLOCATION_PCT = 0.20
# Chosen so a typical setup (~2% ATR/price, 1.5x ATR stop) sizes to
# roughly risk_pct / (stop_atr_multiplier * atr_pct) =~ 0.005 / 0.03 =~
# 17% allocation — comfortably under the 20% cap above, rather than
# routinely exceeding it (0.01 would size to ~33% and self-reject nearly
# every realistic plan).
DEFAULT_RISK_PER_TRADE_PCT = 0.005
DEFAULT_MAX_SECTOR_EXPOSURE_PCT = 0.40
DEFAULT_MIN_RISK_REWARD = 1.5
DEFAULT_MIN_LIQUIDITY_VOLUME = 100_000.0  # minimum acceptable volume_sma_20
DEFAULT_MAX_CONCURRENT_POSITIONS = 5
DEFAULT_FEE_BPS = 15.0
DEFAULT_SLIPPAGE_BPS = 10.0
DEFAULT_STOP_ATR_MULTIPLIER = 1.5
DEFAULT_TARGET_ATR_MULTIPLIER = 3.0


@dataclass(frozen=True, slots=True)
class RiskConfig:
    risk_version: str = RISK_VERSION
    risk_per_trade_pct: float = DEFAULT_RISK_PER_TRADE_PCT
    max_portfolio_exposure_pct: float = DEFAULT_MAX_PORTFOLIO_EXPOSURE_PCT
    max_position_allocation_pct: float = DEFAULT_MAX_POSITION_ALLOCATION_PCT
    max_sector_exposure_pct: float = DEFAULT_MAX_SECTOR_EXPOSURE_PCT
    min_risk_reward: float = DEFAULT_MIN_RISK_REWARD
    min_liquidity_volume: float = DEFAULT_MIN_LIQUIDITY_VOLUME
    max_concurrent_positions: int = DEFAULT_MAX_CONCURRENT_POSITIONS
    fee_bps: float = DEFAULT_FEE_BPS
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS
    stop_atr_multiplier: float = DEFAULT_STOP_ATR_MULTIPLIER
    target_atr_multiplier: float = DEFAULT_TARGET_ATR_MULTIPLIER
    lot_size: int = IDX_LOT_SIZE
