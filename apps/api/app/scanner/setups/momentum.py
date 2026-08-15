"""Momentum continuation: strong established trend with healthy (not
overbought) momentum and confirming MACD histogram.

Prerequisites: sma_50, sma_200, rsi_14, macd_histogram populated.
Qualifying: close > sma_50 > sma_200 AND rsi_14 in [MOMENTUM_RSI_MIN,
MOMENTUM_RSI_MAX] AND macd_histogram > 0.
Invalidation: rsi_14 crosses above 80 (exhaustion), macd_histogram turns
negative, or close closes below sma_50.
"""

from app.db.enums import SetupType
from app.scanner.context import ScanPoint
from app.scanner.scoring_config import MOMENTUM_RSI_MAX, MOMENTUM_RSI_MIN
from app.scanner.setups import SetupResult


def detect(points: list[ScanPoint]) -> SetupResult | None:
    if not points:
        return None

    current = points[-1]
    if (
        current.sma_50 is None
        or current.sma_200 is None
        or current.rsi_14 is None
        or current.macd_histogram is None
    ):
        return None

    if not (current.close > current.sma_50 > current.sma_200):
        return None
    if not (MOMENTUM_RSI_MIN <= current.rsi_14 <= MOMENTUM_RSI_MAX):
        return None
    if current.macd_histogram <= 0:
        return None

    rsi_position = (current.rsi_14 - MOMENTUM_RSI_MIN) / (MOMENTUM_RSI_MAX - MOMENTUM_RSI_MIN)
    quality = max(0.0, min(100.0, rsi_position * 100))

    return SetupResult(
        setup_type=SetupType.MOMENTUM_CONTINUATION,
        reasons=[
            f"trend ordering: close {current.close:.2f} > sma_50 {current.sma_50:.2f} "
            f"> sma_200 {current.sma_200:.2f}",
            f"rsi_14 {current.rsi_14:.1f} in healthy momentum band",
            f"macd_histogram {current.macd_histogram:.4f} positive",
        ],
        invalidation_conditions=[
            "rsi_14 crosses above 80",
            "macd_histogram turns negative",
            f"close closes below sma_50 {current.sma_50:.2f}",
        ],
        setup_quality_score=quality,
    )
