"""Breakout: today's close exceeds the prior 20-day high, on above-average
volume.

Prerequisites: at least 2 points, prior bar's rolling_high_20 populated.
Qualifying: close > prior_bar.rolling_high_20 AND relative_volume >=
BREAKOUT_MIN_RELATIVE_VOLUME.
Invalidation: close falls back below the breakout level (the prior bar's
rolling_high_20 — the level that was broken).

The PRIOR bar's rolling_high_20 is used deliberately, not today's — Phase
3's rolling_high_20 is a trailing window inclusive of the current bar, so
comparing today's close against today's own rolling high would almost
never trigger (today's high is already folded into that window).
"""

from app.db.enums import SetupType
from app.scanner.context import ScanPoint
from app.scanner.scoring_config import BREAKOUT_MIN_RELATIVE_VOLUME
from app.scanner.setups import SetupResult


def detect(points: list[ScanPoint]) -> SetupResult | None:
    if len(points) < 2:
        return None

    current = points[-1]
    prior = points[-2]

    if prior.rolling_high_20 is None or current.relative_volume is None:
        return None

    if current.close <= prior.rolling_high_20:
        return None
    if current.relative_volume < BREAKOUT_MIN_RELATIVE_VOLUME:
        return None

    breakout_pct = (current.close - prior.rolling_high_20) / prior.rolling_high_20
    quality = min(100.0, breakout_pct * 1000)  # 10% above the level -> 100

    return SetupResult(
        setup_type=SetupType.BREAKOUT,
        reasons=[
            f"close {current.close:.2f} broke above prior 20-day high {prior.rolling_high_20:.2f}",
            f"relative volume {current.relative_volume:.2f} >= {BREAKOUT_MIN_RELATIVE_VOLUME}",
        ],
        invalidation_conditions=[f"close falls back below {prior.rolling_high_20:.2f}"],
        setup_quality_score=quality,
    )
