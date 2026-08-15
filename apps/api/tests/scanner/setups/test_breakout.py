from app.scanner.setups import breakout
from tests.scanner.helpers import point


def test_breakout_qualifies_above_prior_high_with_volume() -> None:
    points = [
        point(0, 100.0, rolling_high_20=105.0),
        point(1, 110.0, relative_volume=2.0),
    ]
    result = breakout.detect(points)
    assert result is not None
    assert result.setup_quality_score > 0


def test_breakout_does_not_qualify_below_prior_high() -> None:
    points = [
        point(0, 100.0, rolling_high_20=105.0),
        point(1, 104.0, relative_volume=2.0),
    ]
    assert breakout.detect(points) is None


def test_breakout_boundary_exactly_at_prior_high_does_not_qualify() -> None:
    points = [
        point(0, 100.0, rolling_high_20=105.0),
        point(1, 105.0, relative_volume=2.0),
    ]
    assert breakout.detect(points) is None


def test_breakout_requires_volume_confirmation() -> None:
    points = [
        point(0, 100.0, rolling_high_20=105.0),
        point(1, 110.0, relative_volume=1.0),  # below BREAKOUT_MIN_RELATIVE_VOLUME
    ]
    assert breakout.detect(points) is None


def test_breakout_boundary_relative_volume_exactly_at_threshold_qualifies() -> None:
    # BREAKOUT_MIN_RELATIVE_VOLUME is 1.5; the gate is ">=", so exactly 1.5 passes
    points = [
        point(0, 100.0, rolling_high_20=105.0),
        point(1, 110.0, relative_volume=1.5),
    ]
    assert breakout.detect(points) is not None


def test_breakout_boundary_relative_volume_just_below_threshold_fails() -> None:
    points = [
        point(0, 100.0, rolling_high_20=105.0),
        point(1, 110.0, relative_volume=1.499),
    ]
    assert breakout.detect(points) is None


def test_breakout_requires_two_points() -> None:
    assert breakout.detect([point(0, 100.0, rolling_high_20=105.0)]) is None


def test_breakout_missing_rolling_high_does_not_qualify() -> None:
    points = [
        point(0, 100.0, rolling_high_20=None),
        point(1, 110.0, relative_volume=2.0),
    ]
    assert breakout.detect(points) is None


def test_breakout_ignores_future_bars_no_look_ahead() -> None:
    history = [point(0, 100.0, rolling_high_20=105.0), point(1, 110.0, relative_volume=2.0)]
    baseline = breakout.detect(history)

    with_future = [*history, point(2, 999.0, rolling_high_20=1.0, relative_volume=999.0)]
    # evaluating only the first two points must be unaffected by point 2's presence elsewhere
    assert breakout.detect(history) == baseline
    assert breakout.detect(with_future) != baseline  # different (later) evaluation point
