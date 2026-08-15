"""Pullback continuation: an established uptrend pulls back toward its
20-day EMA without breaking down, RSI cooling to a neutral (not
oversold-crash) band.

Prerequisites: sma_50, sma_200, ema_20, rsi_14 populated on the current bar.
Qualifying: sma_50 > sma_200 (established uptrend) AND close within
PULLBACK_TOLERANCE_PCT of ema_20 AND close >= ema_20 * (1 - tolerance)
(still holding, not broken down) AND rsi_14 in [PULLBACK_RSI_MIN,
PULLBACK_RSI_MAX].
Invalidation: close breaks decisively below ema_20 or below sma_50.
"""

from app.db.enums import SetupType
from app.scanner.context import ScanPoint
from app.scanner.scoring_config import (
    PULLBACK_RSI_MAX,
    PULLBACK_RSI_MIN,
    PULLBACK_TOLERANCE_PCT,
)
from app.scanner.setups import SetupResult


def detect(points: list[ScanPoint]) -> SetupResult | None:
    if not points:
        return None

    current = points[-1]
    if (
        current.sma_50 is None
        or current.sma_200 is None
        or current.ema_20 is None
        or current.rsi_14 is None
    ):
        return None

    if current.sma_50 <= current.sma_200:
        return None

    distance_pct = abs(current.close - current.ema_20) / current.ema_20
    if distance_pct > PULLBACK_TOLERANCE_PCT:
        return None
    if current.close < current.ema_20 * (1 - PULLBACK_TOLERANCE_PCT):
        return None
    if not (PULLBACK_RSI_MIN <= current.rsi_14 <= PULLBACK_RSI_MAX):
        return None

    tightness = 1 - (distance_pct / PULLBACK_TOLERANCE_PCT)
    quality = max(0.0, min(100.0, tightness * 100))

    return SetupResult(
        setup_type=SetupType.PULLBACK_CONTINUATION,
        reasons=[
            f"uptrend intact: sma_50 {current.sma_50:.2f} > sma_200 {current.sma_200:.2f}",
            f"close {current.close:.2f} within {distance_pct:.1%} of ema_20 {current.ema_20:.2f}",
            f"rsi_14 {current.rsi_14:.1f} in neutral pullback band",
        ],
        invalidation_conditions=[
            f"close breaks below ema_20 {current.ema_20:.2f} or sma_50 {current.sma_50:.2f}"
        ],
        setup_quality_score=quality,
    )
