from app.scanner.setups import pullback
from tests.scanner.helpers import point


def test_pullback_qualifies_in_uptrend_near_ema20_neutral_rsi() -> None:
    points = [point(0, 100.0, sma_50=90.0, sma_200=80.0, ema_20=100.5, rsi_14=50.0)]
    result = pullback.detect(points)
    assert result is not None


def test_pullback_does_not_qualify_without_established_uptrend() -> None:
    points = [point(0, 100.0, sma_50=80.0, sma_200=90.0, ema_20=100.5, rsi_14=50.0)]
    assert pullback.detect(points) is None


def test_pullback_does_not_qualify_too_far_from_ema20() -> None:
    points = [point(0, 100.0, sma_50=90.0, sma_200=80.0, ema_20=80.0, rsi_14=50.0)]
    assert pullback.detect(points) is None


def test_pullback_does_not_qualify_rsi_outside_band() -> None:
    points = [point(0, 100.0, sma_50=90.0, sma_200=80.0, ema_20=100.5, rsi_14=80.0)]
    assert pullback.detect(points) is None


def test_pullback_boundary_exactly_at_tolerance_edge_qualifies() -> None:
    # ema_20=100, close=97 -> distance exactly 3% (PULLBACK_TOLERANCE_PCT)
    points = [point(0, 97.0, sma_50=90.0, sma_200=80.0, ema_20=100.0, rsi_14=50.0)]
    result = pullback.detect(points)
    assert result is not None


def test_pullback_missing_indicators_does_not_qualify() -> None:
    points = [point(0, 100.0, sma_50=None, sma_200=80.0, ema_20=100.5, rsi_14=50.0)]
    assert pullback.detect(points) is None
