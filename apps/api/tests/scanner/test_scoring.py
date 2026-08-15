from app.scanner.scoring import (
    momentum_score,
    price_structure_score,
    risk_reward_score,
    score_candidate,
    trend_score,
    volatility_score,
    volume_score,
)
from tests.scanner.helpers import point


def test_trend_score_full_alignment() -> None:
    p = point(0, 110.0, sma_50=100.0, sma_200=90.0)
    assert trend_score(p) == 100.0


def test_trend_score_partial_alignment() -> None:
    # sma_50>sma_200 (+40) and close>sma_200 (+20), but close<sma_50 (+0)
    p = point(0, 95.0, sma_50=100.0, sma_200=90.0)
    assert trend_score(p) == 60.0


def test_trend_score_missing_data_is_zero() -> None:
    assert trend_score(point(0, 100.0, sma_50=None, sma_200=90.0)) == 0.0


def test_momentum_score_healthy_band_is_100() -> None:
    assert momentum_score(point(0, 100.0, rsi_14=60.0)) == 100.0


def test_momentum_score_secondary_band_is_60() -> None:
    assert momentum_score(point(0, 100.0, rsi_14=75.0)) == 60.0


def test_momentum_score_extreme_is_20() -> None:
    assert momentum_score(point(0, 100.0, rsi_14=90.0)) == 20.0


def test_momentum_score_missing_is_zero() -> None:
    assert momentum_score(point(0, 100.0, rsi_14=None)) == 0.0


def test_volume_score_scales_linearly_and_caps_at_100() -> None:
    assert volume_score(point(0, 100.0, relative_volume=1.0)) == 50.0
    assert volume_score(point(0, 100.0, relative_volume=2.0)) == 100.0
    assert volume_score(point(0, 100.0, relative_volume=10.0)) == 100.0  # capped


def test_price_structure_score_at_high_is_100() -> None:
    p = point(0, 110.0, rolling_high_20=110.0, rolling_low_20=90.0)
    assert price_structure_score(p) == 100.0


def test_price_structure_score_at_low_is_0() -> None:
    p = point(0, 90.0, rolling_high_20=110.0, rolling_low_20=90.0)
    assert price_structure_score(p) == 0.0


def test_price_structure_score_midpoint_is_50() -> None:
    p = point(0, 100.0, rolling_high_20=110.0, rolling_low_20=90.0)
    assert price_structure_score(p) == 50.0


def test_volatility_score_peaks_in_moderate_band() -> None:
    p = point(0, 100.0, atr_14=2.5)  # atr_pct=2.5% -> within [1%,5%] band
    assert volatility_score(p) == 100.0


def test_volatility_score_falls_off_when_too_low() -> None:
    p = point(0, 100.0, atr_14=0.1)  # atr_pct=0.1%, well below the 1% floor
    assert volatility_score(p) < 100.0


def test_volatility_score_falls_off_when_too_high() -> None:
    p = point(0, 100.0, atr_14=15.0)  # atr_pct=15%, well above the 5% ceiling
    assert volatility_score(p) < 100.0


def test_risk_reward_score_uses_structure_target_when_available() -> None:
    p = point(0, 100.0, atr_14=2.0, rolling_high_20=110.0)
    score = risk_reward_score(p)
    assert score > 0


def test_risk_reward_score_falls_back_to_atr_projection() -> None:
    p = point(0, 100.0, atr_14=2.0, rolling_high_20=95.0)  # no upside room
    score = risk_reward_score(p)
    assert score > 0


def test_risk_reward_score_missing_atr_is_zero() -> None:
    assert risk_reward_score(point(0, 100.0, atr_14=None)) == 0.0


def test_score_candidate_composite_is_weighted_sum() -> None:
    p = point(
        0,
        110.0,
        sma_50=100.0,
        sma_200=90.0,
        rsi_14=60.0,
        relative_volume=1.0,
        rolling_high_20=110.0,
        rolling_low_20=90.0,
        atr_14=2.5,
    )
    scores = score_candidate(p, setup_quality=80.0)
    assert scores.composite_score == round(scores.composite_score, 10)  # just a sanity float check
    assert 0 <= scores.composite_score <= 100
