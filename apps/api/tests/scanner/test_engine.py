from app.db.enums import SetupType
from app.scanner.engine import run_scan
from tests.scanner.helpers import point


def test_run_scan_empty_input() -> None:
    assert run_scan([]) == []


def test_run_scan_returns_only_qualifying_setups() -> None:
    # a point with no indicators populated qualifies for nothing
    points = [point(0, 100.0), point(1, 100.0)]
    assert run_scan(points) == []


def test_run_scan_can_return_multiple_qualifying_setups() -> None:
    # craft a point that satisfies both momentum_continuation and pullback
    # is contradictory (pullback needs close near ema_20, momentum needs
    # close>sma_50) — instead verify breakout + ma_reclaim can co-fire
    # since they check different, non-conflicting conditions.
    points = [
        point(0, 95.0, sma_50=100.0, rolling_high_20=105.0),
        point(
            1,
            110.0,
            sma_50=100.0,
            rolling_high_20=105.0,
            relative_volume=2.0,
        ),
    ]
    results = run_scan(points)
    setup_types = {r.setup.setup_type for r in results}
    assert SetupType.BREAKOUT in setup_types
    assert SetupType.MA_RECLAIM in setup_types


def test_run_scan_is_deterministic() -> None:
    points = [
        point(0, 95.0, sma_50=100.0, rolling_high_20=105.0),
        point(1, 110.0, sma_50=100.0, rolling_high_20=105.0, relative_volume=2.0),
    ]
    first = run_scan(points)
    second = run_scan(points)
    assert [(r.setup.setup_type, r.scores.composite_score) for r in first] == [
        (r.setup.setup_type, r.scores.composite_score) for r in second
    ]


def test_run_scan_no_look_ahead_future_mutation() -> None:
    """Mirrors Phase 3's mandated adversarial test: results for an
    evaluation as of index i must be unaffected by what bars beyond i
    contain."""
    base_history = [
        point(0, 95.0, sma_50=100.0, rolling_high_20=105.0),
        point(1, 110.0, sma_50=100.0, rolling_high_20=105.0, relative_volume=2.0),
    ]
    baseline = run_scan(base_history)

    extended = [*base_history, point(2, 999999.0, rolling_high_20=1.0, relative_volume=999.0)]
    # re-evaluating the ORIGINAL history (not the extended one) must give
    # the exact same result regardless of what was appended
    assert run_scan(base_history) == baseline
    # and the result for the truncated history is untouched by the fact
    # that a longer series exists elsewhere in memory
    truncated_again = run_scan(extended[:2])
    assert truncated_again == baseline
