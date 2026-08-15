from app.scanner.setups import momentum
from tests.scanner.helpers import point


def test_momentum_qualifies_strong_trend_healthy_rsi_positive_macd() -> None:
    points = [point(0, 110.0, sma_50=100.0, sma_200=90.0, rsi_14=60.0, macd_histogram=0.5)]
    assert momentum.detect(points) is not None


def test_momentum_does_not_qualify_without_trend_ordering() -> None:
    points = [point(0, 90.0, sma_50=100.0, sma_200=90.0, rsi_14=60.0, macd_histogram=0.5)]
    assert momentum.detect(points) is None


def test_momentum_does_not_qualify_overbought_rsi() -> None:
    points = [point(0, 110.0, sma_50=100.0, sma_200=90.0, rsi_14=85.0, macd_histogram=0.5)]
    assert momentum.detect(points) is None


def test_momentum_does_not_qualify_negative_macd_histogram() -> None:
    points = [point(0, 110.0, sma_50=100.0, sma_200=90.0, rsi_14=60.0, macd_histogram=-0.1)]
    assert momentum.detect(points) is None


def test_momentum_boundary_rsi_exactly_at_band_edges_qualifies() -> None:
    points = [point(0, 110.0, sma_50=100.0, sma_200=90.0, rsi_14=50.0, macd_histogram=0.5)]
    assert momentum.detect(points) is not None
    points2 = [point(0, 110.0, sma_50=100.0, sma_200=90.0, rsi_14=70.0, macd_histogram=0.5)]
    assert momentum.detect(points2) is not None
