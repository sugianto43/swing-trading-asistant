"""Canonical alert-engine configuration. Bump ALERT_VERSION whenever a
trigger formula/threshold changes, so historical alerts stay traceable
to the exact configuration that produced them (MASTER-PRD §21).

Thresholds are illustrative starting values, not verified real trading
signals — same "not a verified real assumption" caveat as backtesting's
fee/slippage defaults and Phase 9's regime thresholds.
"""

from dataclasses import dataclass

ALERT_VERSION = "v1"

DEFAULT_NEAR_PRICE_THRESHOLD_PCT = 0.02  # within 2% counts as "near" entry/stop/target
DEFAULT_UNUSUAL_VOLUME_RELATIVE_THRESHOLD = 2.0  # relative_volume >= 2x counts as "unusual"


@dataclass(frozen=True, slots=True)
class AlertConfig:
    alert_version: str = ALERT_VERSION
    near_price_threshold_pct: float = DEFAULT_NEAR_PRICE_THRESHOLD_PCT
    unusual_volume_relative_threshold: float = DEFAULT_UNUSUAL_VOLUME_RELATIVE_THRESHOLD
