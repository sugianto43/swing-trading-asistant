"""Volatility contraction -> expansion (Bollinger squeeze): Bollinger Band
width contracts to a recent low, then price breaks out above the upper
band on above-average volume.

Prerequisites: at least 2 points with bb_upper/bb_middle/bb_lower
populated; enough trailing history (up to SQUEEZE_LOOKBACK points) to
judge what "contracted" means for this instrument.
Qualifying: the PRIOR bar's band width was in the tightest
SQUEEZE_PERCENTILE fraction of the trailing lookback AND today's close
breaks above today's bb_upper AND relative_volume >=
SQUEEZE_MIN_RELATIVE_VOLUME.
Invalidation: close falls back inside the bands (below bb_upper).
"""

from app.db.enums import SetupType
from app.scanner.context import ScanPoint
from app.scanner.scoring_config import (
    SQUEEZE_LOOKBACK,
    SQUEEZE_MIN_RELATIVE_VOLUME,
    SQUEEZE_PERCENTILE,
)
from app.scanner.setups import SetupResult


def _band_width(point: ScanPoint) -> float | None:
    if point.bb_upper is None or point.bb_lower is None or point.bb_middle is None:
        return None
    if point.bb_middle == 0:
        return None
    return (point.bb_upper - point.bb_lower) / point.bb_middle


def detect(points: list[ScanPoint]) -> SetupResult | None:
    if len(points) < 2:
        return None

    current = points[-1]
    prior = points[-2]

    if current.bb_upper is None or current.relative_volume is None:
        return None

    prior_width = _band_width(prior)
    if prior_width is None:
        return None

    history = points[:-1][-SQUEEZE_LOOKBACK:]
    widths = sorted(w for p in history if (w := _band_width(p)) is not None)
    if len(widths) < 5:  # need a meaningful sample to judge a percentile against
        return None

    threshold_index = max(0, int(len(widths) * SQUEEZE_PERCENTILE) - 1)
    threshold = widths[threshold_index]
    if prior_width > threshold:
        return None

    if current.close <= current.bb_upper:
        return None
    if current.relative_volume < SQUEEZE_MIN_RELATIVE_VOLUME:
        return None

    breakout_pct = (current.close - current.bb_upper) / current.bb_upper
    quality = min(100.0, breakout_pct * 1500)

    return SetupResult(
        setup_type=SetupType.VOLATILITY_SQUEEZE,
        reasons=[
            f"band width contracted to tightest {SQUEEZE_PERCENTILE:.0%} of "
            f"trailing {SQUEEZE_LOOKBACK}-day range",
            f"close {current.close:.2f} broke above upper band {current.bb_upper:.2f}",
            f"relative volume {current.relative_volume:.2f} >= {SQUEEZE_MIN_RELATIVE_VOLUME}",
        ],
        invalidation_conditions=[f"close falls back below upper band {current.bb_upper:.2f}"],
        setup_quality_score=quality,
    )
