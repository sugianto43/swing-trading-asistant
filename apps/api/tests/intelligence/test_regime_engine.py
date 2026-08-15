from app.db.enums import MarketRegime
from app.intelligence.breadth_engine import BreadthResult
from app.intelligence.config import RegimeConfig
from app.intelligence.regime_engine import classify_regime

CONFIG = RegimeConfig(risk_on_threshold=0.60, risk_off_threshold=0.40)


def _breadth(pct_above_sma50, advancers=0, decliners=0):
    return BreadthResult(
        universe_size=10,
        pct_above_sma50=pct_above_sma50,
        pct_above_sma200=None,
        advancers=advancers,
        decliners=decliners,
        unchanged=0,
        new_highs_20=0,
        new_lows_20=0,
    )


def test_classify_risk_on() -> None:
    result = classify_regime(_breadth(0.70, advancers=8, decliners=2), CONFIG)
    assert result.regime == MarketRegime.RISK_ON


def test_classify_risk_off() -> None:
    result = classify_regime(_breadth(0.20, advancers=2, decliners=8), CONFIG)
    assert result.regime == MarketRegime.RISK_OFF


def test_classify_neutral_mid_breadth() -> None:
    result = classify_regime(_breadth(0.50, advancers=5, decliners=5), CONFIG)
    assert result.regime == MarketRegime.NEUTRAL


def test_classify_neutral_high_breadth_but_more_decliners() -> None:
    """High pct_above_sma50 alone isn't enough — advance/decline must
    also agree, otherwise it's a conflicting signal, not RISK_ON."""
    result = classify_regime(_breadth(0.70, advancers=3, decliners=7), CONFIG)
    assert result.regime == MarketRegime.NEUTRAL


def test_classify_boundary_exactly_at_risk_on_threshold() -> None:
    result = classify_regime(_breadth(0.60, advancers=6, decliners=4), CONFIG)
    assert result.regime == MarketRegime.RISK_ON  # >= threshold, inclusive


def test_classify_boundary_exactly_at_risk_off_threshold() -> None:
    result = classify_regime(_breadth(0.40, advancers=4, decliners=6), CONFIG)
    assert result.regime == MarketRegime.RISK_OFF  # <= threshold, inclusive


def test_classify_boundary_just_below_risk_on_threshold() -> None:
    result = classify_regime(_breadth(0.599, advancers=6, decliners=4), CONFIG)
    assert result.regime == MarketRegime.NEUTRAL


def test_classify_missing_breadth_data_is_neutral_never_guessed() -> None:
    result = classify_regime(_breadth(None), CONFIG)
    assert result.regime == MarketRegime.NEUTRAL


def test_classify_records_config_version() -> None:
    config = RegimeConfig(regime_version="v2", risk_on_threshold=0.6, risk_off_threshold=0.4)
    result = classify_regime(_breadth(0.70, advancers=8, decliners=2), config)
    assert result.regime_version == "v2"
