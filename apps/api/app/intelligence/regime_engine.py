"""Pure regime classification from a breadth snapshot. No DB access."""

from dataclasses import dataclass

from app.db.enums import MarketRegime
from app.intelligence.breadth_engine import BreadthResult
from app.intelligence.config import RegimeConfig


@dataclass(frozen=True, slots=True)
class RegimeClassification:
    regime: MarketRegime
    regime_version: str


def classify_regime(breadth: BreadthResult, config: RegimeConfig) -> RegimeClassification:
    """RISK_ON: breadth strongly positive (>= risk_on_threshold above
    SMA50) AND more advancers than decliners. RISK_OFF: the symmetric
    negative case. Anything else — including insufficient data to
    compute pct_above_sma50 at all — is NEUTRAL, never guessed toward
    either side.
    """
    if breadth.pct_above_sma50 is None:
        return RegimeClassification(
            regime=MarketRegime.NEUTRAL, regime_version=config.regime_version
        )

    if (
        breadth.pct_above_sma50 >= config.risk_on_threshold
        and breadth.advancers > breadth.decliners
    ):
        regime = MarketRegime.RISK_ON
    elif (
        breadth.pct_above_sma50 <= config.risk_off_threshold
        and breadth.decliners > breadth.advancers
    ):
        regime = MarketRegime.RISK_OFF
    else:
        regime = MarketRegime.NEUTRAL

    return RegimeClassification(regime=regime, regime_version=config.regime_version)
