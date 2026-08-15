"""Canonical market-intelligence configuration.

Bump BREADTH_VERSION whenever the breadth formula changes, and
REGIME_VERSION whenever the regime classification rule/thresholds
change — so historical breadth_snapshots rows stay traceable to the
exact configuration that produced them (MASTER-PRD §21), mirroring
indicator_version/score_version/risk_version.

Regime thresholds are illustrative starting values, not a verified
market-timing signal — same "not a verified real assumption" caveat as
backtesting's fee/slippage defaults (app/backtesting/config.py).
"""

from dataclasses import dataclass

BREADTH_VERSION = "v1"
REGIME_VERSION = "v1"

DEFAULT_RISK_ON_PCT_ABOVE_SMA50 = 0.60
DEFAULT_RISK_OFF_PCT_ABOVE_SMA50 = 0.40


@dataclass(frozen=True, slots=True)
class RegimeConfig:
    regime_version: str = REGIME_VERSION
    risk_on_threshold: float = DEFAULT_RISK_ON_PCT_ABOVE_SMA50
    risk_off_threshold: float = DEFAULT_RISK_OFF_PCT_ABOVE_SMA50
