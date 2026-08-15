from app.scanner.setups import volatility_squeeze
from tests.scanner.helpers import point


def _band_point(day_offset: int, width: float, close: float = 100.0, **kwargs):
    # bb_middle=100 always; bb_upper/bb_lower encode the desired band width
    # since (bb_upper - bb_lower) / bb_middle == width by construction.
    return point(
        day_offset,
        close,
        bb_upper=100 + 50 * width,
        bb_middle=100.0,
        bb_lower=100 - 50 * width,
        **kwargs,
    )


def test_squeeze_qualifies_after_contraction_and_breakout() -> None:
    history = [_band_point(i, 0.30) for i in range(15)] + [
        _band_point(15 + i, 0.02) for i in range(5)
    ]
    current = point(20, 106.0, bb_upper=101.0, bb_middle=100.0, bb_lower=99.0, relative_volume=1.5)
    points = [*history, current]

    result = volatility_squeeze.detect(points)
    assert result is not None


def test_squeeze_does_not_qualify_when_prior_bar_not_contracted() -> None:
    history = [_band_point(i, 0.02) for i in range(19)] + [_band_point(19, 0.30)]
    current = point(20, 106.0, bb_upper=101.0, bb_middle=100.0, bb_lower=99.0, relative_volume=1.5)
    points = [*history, current]

    assert volatility_squeeze.detect(points) is None


def test_squeeze_does_not_qualify_without_breakout_above_band() -> None:
    history = [_band_point(i, 0.30) for i in range(15)] + [
        _band_point(15 + i, 0.02) for i in range(5)
    ]
    current = point(20, 100.5, bb_upper=101.0, bb_middle=100.0, bb_lower=99.0, relative_volume=1.5)
    points = [*history, current]

    assert volatility_squeeze.detect(points) is None


def test_squeeze_requires_volume_confirmation() -> None:
    history = [_band_point(i, 0.30) for i in range(15)] + [
        _band_point(15 + i, 0.02) for i in range(5)
    ]
    current = point(20, 106.0, bb_upper=101.0, bb_middle=100.0, bb_lower=99.0, relative_volume=1.0)
    points = [*history, current]

    assert volatility_squeeze.detect(points) is None


def test_squeeze_boundary_relative_volume_exactly_at_threshold_qualifies() -> None:
    # SQUEEZE_MIN_RELATIVE_VOLUME is 1.3
    history = [_band_point(i, 0.30) for i in range(15)] + [
        _band_point(15 + i, 0.02) for i in range(5)
    ]
    current = point(20, 106.0, bb_upper=101.0, bb_middle=100.0, bb_lower=99.0, relative_volume=1.3)
    points = [*history, current]

    assert volatility_squeeze.detect(points) is not None


def test_squeeze_boundary_close_exactly_at_upper_band_does_not_qualify() -> None:
    history = [_band_point(i, 0.30) for i in range(15)] + [
        _band_point(15 + i, 0.02) for i in range(5)
    ]
    current = point(20, 101.0, bb_upper=101.0, bb_middle=100.0, bb_lower=99.0, relative_volume=1.5)
    points = [*history, current]

    assert volatility_squeeze.detect(points) is None


def test_squeeze_insufficient_history_does_not_qualify() -> None:
    history = [_band_point(i, 0.02) for i in range(2)]
    current = point(3, 106.0, bb_upper=101.0, bb_middle=100.0, bb_lower=99.0, relative_volume=1.5)
    points = [*history, current]

    assert volatility_squeeze.detect(points) is None
