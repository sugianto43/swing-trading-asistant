"""Pure market-breadth calculation over one day's cross-section of the
(survivorship-correct) instrument universe. No DB access — same
discipline as app/risk/engine.py and app/positions/position_engine.py.

Breadth here is a proxy for the LOCAL universe actually ingested, not a
claim about the whole IDX market — a documented limitation (README),
not a silent one.
"""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BreadthInput:
    """One instrument's cross-sectional data point for a given date."""

    instrument_id: uuid.UUID
    close: float
    prior_close: float | None
    sma_50: float | None
    sma_200: float | None
    rolling_high_20: float | None
    rolling_low_20: float | None


@dataclass(frozen=True, slots=True)
class BreadthResult:
    universe_size: int
    pct_above_sma50: float | None
    pct_above_sma200: float | None
    advancers: int
    decliners: int
    unchanged: int
    new_highs_20: int
    new_lows_20: int


def compute_breadth(points: list[BreadthInput]) -> BreadthResult:
    """Deterministic, order-independent aggregation. Instruments missing
    a given indicator (e.g. SMA200 not yet warmed up) are excluded from
    that specific ratio's denominator, never counted as "below" it —
    excluding is honest about missing data, silently treating it as a
    negative signal would not be.
    """
    universe_size = len(points)

    sma50_pairs = [(p.close, p.sma_50) for p in points if p.sma_50 is not None]
    pct_above_sma50 = (
        sum(1 for close, sma in sma50_pairs if close > sma) / len(sma50_pairs)
        if sma50_pairs
        else None
    )

    sma200_pairs = [(p.close, p.sma_200) for p in points if p.sma_200 is not None]
    pct_above_sma200 = (
        sum(1 for close, sma in sma200_pairs if close > sma) / len(sma200_pairs)
        if sma200_pairs
        else None
    )

    prior_pairs = [(p.close, p.prior_close) for p in points if p.prior_close is not None]
    advancers = sum(1 for close, prior in prior_pairs if close > prior)
    decliners = sum(1 for close, prior in prior_pairs if close < prior)
    unchanged = sum(1 for close, prior in prior_pairs if close == prior)

    new_highs_20 = sum(
        1 for p in points if p.rolling_high_20 is not None and p.close >= p.rolling_high_20
    )
    new_lows_20 = sum(
        1 for p in points if p.rolling_low_20 is not None and p.close <= p.rolling_low_20
    )

    return BreadthResult(
        universe_size=universe_size,
        pct_above_sma50=pct_above_sma50,
        pct_above_sma200=pct_above_sma200,
        advancers=advancers,
        decliners=decliners,
        unchanged=unchanged,
        new_highs_20=new_highs_20,
        new_lows_20=new_lows_20,
    )
