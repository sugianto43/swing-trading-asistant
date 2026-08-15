from dataclasses import dataclass
from datetime import date

from app.scanner.context import ScanPoint
from app.scanner.scoring import ComponentScores, score_candidate
from app.scanner.scoring_config import SCORE_VERSION
from app.scanner.setups import (
    SetupResult,
    breakout,
    ma_reclaim,
    momentum,
    pullback,
    volatility_squeeze,
)

_DETECTORS = (breakout, pullback, momentum, ma_reclaim, volatility_squeeze)


@dataclass(frozen=True, slots=True)
class CandidateResult:
    trade_date: date
    setup: SetupResult
    scores: ComponentScores
    score_version: str


def run_scan(points: list[ScanPoint]) -> list[CandidateResult]:
    """Evaluate every canonical setup against the most recent point in
    `points` (the rest is history for lookback/warm-up). Only qualifying
    setups produce a result — a non-qualifying setup is absent, not a
    zero-score entry."""
    if not points:
        return []

    current_date = points[-1].trade_date
    results: list[CandidateResult] = []
    for detector in _DETECTORS:
        setup_result = detector.detect(points)
        if setup_result is None:
            continue
        scores = score_candidate(points[-1], setup_result.setup_quality_score)
        results.append(
            CandidateResult(
                trade_date=current_date,
                setup=setup_result,
                scores=scores,
                score_version=SCORE_VERSION,
            )
        )
    return results
