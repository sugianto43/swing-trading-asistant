"""Candidate scoring: six generic components (trend, momentum, volume,
price structure, volatility, risk/reward) plus the setup-specific
setup_quality_score already computed by the detector, combined into a
single weighted composite (MASTER-PRD FR-006: configurable, explainable,
versioned — never a probability of profit, a ranking heuristic only).

Every formula here is deliberately simple and documented so the score is
auditable, not a black box (MASTER-PRD §6 Transparency). Missing/
insufficient data always yields a 0 component score, never a fabricated
guess.
"""

from dataclasses import dataclass

from app.scanner.context import ScanPoint
from app.scanner.scoring_config import (
    RISK_REWARD_ATR_STOP_MULTIPLIER,
    RISK_REWARD_ATR_TARGET_MULTIPLIER,
    RISK_REWARD_SCORE_SCALE,
    SCORE_WEIGHTS,
    VOLATILITY_HIGH_BAND,
    VOLATILITY_LOW_BAND,
    VOLUME_SCORE_SCALE,
)


@dataclass(frozen=True, slots=True)
class ComponentScores:
    trend_score: float
    momentum_score: float
    volume_score: float
    price_structure_score: float
    volatility_score: float
    setup_quality_score: float
    risk_reward_score: float

    @property
    def composite_score(self) -> float:
        fields: dict[str, float] = {
            "trend_score": self.trend_score,
            "momentum_score": self.momentum_score,
            "volume_score": self.volume_score,
            "price_structure_score": self.price_structure_score,
            "volatility_score": self.volatility_score,
            "setup_quality_score": self.setup_quality_score,
            "risk_reward_score": self.risk_reward_score,
        }
        return sum(fields[name] * weight for name, weight in SCORE_WEIGHTS.items())


def _clip(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def trend_score(point: ScanPoint) -> float:
    """0-100: rewards close>sma_50, sma_50>sma_200, and close>sma_200
    ordering independently, so a partial trend still scores partially."""
    if point.sma_50 is None or point.sma_200 is None:
        return 0.0
    score = 0.0
    if point.close > point.sma_50:
        score += 40.0
    if point.sma_50 > point.sma_200:
        score += 40.0
    if point.close > point.sma_200:
        score += 20.0
    return score


def momentum_score(point: ScanPoint) -> float:
    """0-100 from RSI band: 50-70 is the healthy momentum zone; 40-50 or
    70-80 is a weaker but acceptable secondary band; outside that is
    either too weak or overbought/exhausted."""
    if point.rsi_14 is None:
        return 0.0
    rsi = point.rsi_14
    if 50 <= rsi <= 70:
        return 100.0
    if 40 <= rsi < 50 or 70 < rsi <= 80:
        return 60.0
    return 20.0


def volume_score(point: ScanPoint) -> float:
    """0-100, linear in relative_volume: 2.0x average -> 100, 1.0x -> 50."""
    if point.relative_volume is None:
        return 0.0
    return _clip(point.relative_volume * VOLUME_SCORE_SCALE)


def price_structure_score(point: ScanPoint) -> float:
    """0-100: position of close within its trailing 20-day high/low range."""
    if point.rolling_high_20 is None or point.rolling_low_20 is None:
        return 0.0
    range_size = point.rolling_high_20 - point.rolling_low_20
    if range_size <= 0:
        return 0.0
    position = (point.close - point.rolling_low_20) / range_size
    return _clip(position * 100)


def volatility_score(point: ScanPoint) -> float:
    """0-100: prefers a moderate ATR/close ratio — too low reads as
    illiquid/dead, too high reads as excessively risky for a weekly-swing
    hold. Peaks at 100 in the middle of [VOLATILITY_LOW_BAND,
    VOLATILITY_HIGH_BAND], falls off linearly outside it."""
    if point.atr_14 is None or point.close == 0:
        return 0.0
    atr_pct = point.atr_14 / point.close
    if atr_pct < VOLATILITY_LOW_BAND:
        return _clip(100 * (atr_pct / VOLATILITY_LOW_BAND))
    if atr_pct > VOLATILITY_HIGH_BAND:
        overshoot = (atr_pct - VOLATILITY_HIGH_BAND) / VOLATILITY_HIGH_BAND
        return _clip(100 - overshoot * 100)
    return 100.0


def risk_reward_score(point: ScanPoint) -> float:
    """0-100 from an ATR-based stop and a structure-based (or, lacking
    upside room, ATR-projected) target — a ranking heuristic only, not a
    trade plan. Phase 6 owns real position sizing/stop/target."""
    if point.atr_14 is None or point.close <= 0:
        return 0.0

    stop = point.close - RISK_REWARD_ATR_STOP_MULTIPLIER * point.atr_14
    risk = point.close - stop
    if risk <= 0:
        return 0.0

    if point.rolling_high_20 is not None and point.rolling_high_20 > point.close:
        target = point.rolling_high_20
    else:
        target = point.close + RISK_REWARD_ATR_TARGET_MULTIPLIER * point.atr_14

    reward = target - point.close
    if reward <= 0:
        return 0.0

    ratio = reward / risk
    return _clip(ratio * RISK_REWARD_SCORE_SCALE)


def score_candidate(point: ScanPoint, setup_quality: float) -> ComponentScores:
    return ComponentScores(
        trend_score=trend_score(point),
        momentum_score=momentum_score(point),
        volume_score=volume_score(point),
        price_structure_score=price_structure_score(point),
        volatility_score=volatility_score(point),
        setup_quality_score=_clip(setup_quality),
        risk_reward_score=risk_reward_score(point),
    )
