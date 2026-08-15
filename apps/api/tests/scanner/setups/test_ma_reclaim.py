from app.scanner.setups import ma_reclaim
from tests.scanner.helpers import point


def test_ma_reclaim_qualifies_on_genuine_crossover() -> None:
    points = [
        point(0, 95.0, sma_50=100.0),  # below
        point(1, 105.0, sma_50=100.0, relative_volume=1.5),  # above
    ]
    assert ma_reclaim.detect(points) is not None


def test_ma_reclaim_does_not_qualify_already_above() -> None:
    points = [
        point(0, 105.0, sma_50=100.0),
        point(1, 106.0, sma_50=100.0, relative_volume=1.5),
    ]
    assert ma_reclaim.detect(points) is None


def test_ma_reclaim_does_not_qualify_still_below() -> None:
    points = [
        point(0, 95.0, sma_50=100.0),
        point(1, 98.0, sma_50=100.0, relative_volume=1.5),
    ]
    assert ma_reclaim.detect(points) is None


def test_ma_reclaim_requires_volume_confirmation() -> None:
    points = [
        point(0, 95.0, sma_50=100.0),
        point(1, 105.0, sma_50=100.0, relative_volume=0.5),
    ]
    assert ma_reclaim.detect(points) is None


def test_ma_reclaim_requires_two_points() -> None:
    assert ma_reclaim.detect([point(0, 105.0, sma_50=100.0)]) is None


def test_ma_reclaim_boundary_relative_volume_exactly_at_threshold_qualifies() -> None:
    # MA_RECLAIM_MIN_RELATIVE_VOLUME is 1.0
    points = [
        point(0, 95.0, sma_50=100.0),
        point(1, 105.0, sma_50=100.0, relative_volume=1.0),
    ]
    assert ma_reclaim.detect(points) is not None


def test_ma_reclaim_boundary_close_exactly_at_sma50_does_not_qualify() -> None:
    # "above" must be a strict >, not >=
    points = [
        point(0, 95.0, sma_50=100.0),
        point(1, 100.0, sma_50=100.0, relative_volume=1.5),
    ]
    assert ma_reclaim.detect(points) is None
