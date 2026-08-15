"""Moving-average reclaim: price crosses back above the 50-day SMA after
being below it, on at least average volume.

Prerequisites: sma_50 populated on both the current and prior bar.
Qualifying: prior.close < prior.sma_50 (was below) AND current.close >
current.sma_50 (now above) — a genuine crossover on this bar AND
relative_volume >= MA_RECLAIM_MIN_RELATIVE_VOLUME.
Invalidation: close falls back below sma_50.
"""

from app.db.enums import SetupType
from app.scanner.context import ScanPoint
from app.scanner.scoring_config import MA_RECLAIM_MIN_RELATIVE_VOLUME
from app.scanner.setups import SetupResult


def detect(points: list[ScanPoint]) -> SetupResult | None:
    if len(points) < 2:
        return None

    current = points[-1]
    prior = points[-2]

    if current.sma_50 is None or prior.sma_50 is None or current.relative_volume is None:
        return None

    if not (prior.close < prior.sma_50 and current.close > current.sma_50):
        return None
    if current.relative_volume < MA_RECLAIM_MIN_RELATIVE_VOLUME:
        return None

    reclaim_pct = (current.close - current.sma_50) / current.sma_50
    quality = min(100.0, reclaim_pct * 2000)  # 5% above sma_50 -> 100

    return SetupResult(
        setup_type=SetupType.MA_RECLAIM,
        reasons=[
            f"close crossed from below {prior.sma_50:.2f} to above {current.sma_50:.2f} sma_50",
            f"relative volume {current.relative_volume:.2f} >= {MA_RECLAIM_MIN_RELATIVE_VOLUME}",
        ],
        invalidation_conditions=[f"close falls back below sma_50 {current.sma_50:.2f}"],
        setup_quality_score=quality,
    )
