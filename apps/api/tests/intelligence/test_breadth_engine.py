import uuid

from app.intelligence.breadth_engine import BreadthInput, compute_breadth


def _point(close, prior_close=None, sma_50=None, sma_200=None, high20=None, low20=None):
    return BreadthInput(
        instrument_id=uuid.uuid4(),
        close=close,
        prior_close=prior_close,
        sma_50=sma_50,
        sma_200=sma_200,
        rolling_high_20=high20,
        rolling_low_20=low20,
    )


def test_compute_breadth_empty_universe() -> None:
    result = compute_breadth([])
    assert result.universe_size == 0
    assert result.pct_above_sma50 is None
    assert result.pct_above_sma200 is None
    assert result.advancers == 0
    assert result.decliners == 0
    assert result.unchanged == 0


def test_compute_breadth_all_above_sma50() -> None:
    points = [_point(close=110, sma_50=100), _point(close=120, sma_50=100)]
    result = compute_breadth(points)
    assert result.pct_above_sma50 == 1.0


def test_compute_breadth_none_above_sma50() -> None:
    points = [_point(close=90, sma_50=100), _point(close=95, sma_50=100)]
    result = compute_breadth(points)
    assert result.pct_above_sma50 == 0.0


def test_compute_breadth_mixed_pct_above_sma50() -> None:
    points = [_point(close=110, sma_50=100), _point(close=90, sma_50=100)]
    result = compute_breadth(points)
    assert result.pct_above_sma50 == 0.5


def test_compute_breadth_missing_sma_excluded_not_fabricated() -> None:
    """An instrument with no SMA50 yet (not warmed up) must be excluded
    from that ratio's denominator entirely, never counted as 'below'."""
    points = [_point(close=110, sma_50=100), _point(close=90, sma_50=None)]
    result = compute_breadth(points)
    assert result.pct_above_sma50 == 1.0  # only the one instrument with data counted
    assert result.universe_size == 2  # but universe_size still reflects everyone


def test_compute_breadth_advancers_decliners_unchanged() -> None:
    points = [
        _point(close=110, prior_close=100),  # advancer
        _point(close=90, prior_close=100),  # decliner
        _point(close=100, prior_close=100),  # unchanged
        _point(close=50, prior_close=None),  # excluded — no prior close
    ]
    result = compute_breadth(points)
    assert result.advancers == 1
    assert result.decliners == 1
    assert result.unchanged == 1


def test_compute_breadth_new_highs_and_lows() -> None:
    points = [
        _point(close=100, high20=100, low20=80),  # new high (close == rolling high)
        _point(close=80, high20=100, low20=80),  # new low (close == rolling low)
        _point(close=90, high20=100, low20=80),  # neither
    ]
    result = compute_breadth(points)
    assert result.new_highs_20 == 1
    assert result.new_lows_20 == 1


def test_compute_breadth_deterministic_reproducible() -> None:
    points = [_point(close=110, prior_close=100, sma_50=100, sma_200=90, high20=110, low20=80)]
    first = compute_breadth(points)
    second = compute_breadth(points)
    assert first == second
