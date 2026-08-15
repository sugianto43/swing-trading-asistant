from datetime import date, timedelta

from app.db.enums import DataQualityStatus
from app.marketdata.provider import RawBar, RawCalendarDay
from app.marketdata.validation import (
    classify_quality,
    find_duplicate_trade_dates,
    find_missing_sessions,
    is_stale,
    validate_bar,
)

AS_OF = date(2024, 1, 10)


def _bar(**overrides) -> RawBar:
    defaults = {
        "source_symbol": "BBCA.JK",
        "trade_date": date(2024, 1, 5),
        "open": 100.0,
        "high": 105.0,
        "low": 95.0,
        "close": 102.0,
        "volume": 1000,
        "source": "fixture",
    }
    defaults.update(overrides)
    return RawBar(**defaults)


def test_valid_bar_has_no_issues() -> None:
    issues = validate_bar(_bar(), as_of=AS_OF)
    assert issues == []
    assert classify_quality(issues) == DataQualityStatus.VALID


def test_future_dated_bar_is_invalid() -> None:
    bar = _bar(trade_date=AS_OF + timedelta(days=1))
    issues = validate_bar(bar, as_of=AS_OF)
    assert "FUTURE_DATED_BAR" in issues
    assert classify_quality(issues) == DataQualityStatus.INVALID


def test_negative_price_is_invalid() -> None:
    bar = _bar(low=-5)
    issues = validate_bar(bar, as_of=AS_OF)
    assert "NON_POSITIVE_PRICE" in issues
    assert classify_quality(issues) == DataQualityStatus.INVALID


def test_zero_price_is_invalid() -> None:
    bar = _bar(close=0)
    issues = validate_bar(bar, as_of=AS_OF)
    assert "NON_POSITIVE_PRICE" in issues


def test_negative_volume_is_invalid() -> None:
    bar = _bar(volume=-1)
    issues = validate_bar(bar, as_of=AS_OF)
    assert "NEGATIVE_VOLUME" in issues
    assert classify_quality(issues) == DataQualityStatus.INVALID


def test_high_below_other_prices_is_invalid() -> None:
    bar = _bar(high=90, open=100, close=95, low=85)
    issues = validate_bar(bar, as_of=AS_OF)
    assert "HIGH_BELOW_OTHER_PRICES" in issues


def test_low_above_other_prices_is_invalid() -> None:
    bar = _bar(low=110, open=100, close=95, high=115)
    issues = validate_bar(bar, as_of=AS_OF)
    assert "LOW_ABOVE_OTHER_PRICES" in issues


def test_abnormal_volume_flagged_suspect_not_invalid() -> None:
    previous = _bar(volume=1000, trade_date=date(2024, 1, 4))
    current = _bar(volume=50000, trade_date=date(2024, 1, 5))
    issues = validate_bar(current, as_of=AS_OF, previous_bar=previous)
    assert "ABNORMAL_VOLUME" in issues
    assert classify_quality(issues) == DataQualityStatus.SUSPECT


def test_zero_volume_is_valid_boundary() -> None:
    # zero volume alone (e.g. a suspended-but-listed day) is not an error
    bar = _bar(volume=0)
    issues = validate_bar(bar, as_of=AS_OF)
    assert issues == []


def test_find_duplicate_trade_dates() -> None:
    bars = [
        _bar(trade_date=date(2024, 1, 2)),
        _bar(trade_date=date(2024, 1, 3)),
        _bar(trade_date=date(2024, 1, 3)),
    ]
    duplicates = find_duplicate_trade_dates(bars)
    assert duplicates == {date(2024, 1, 3): 2}


def test_find_duplicate_trade_dates_none_when_unique() -> None:
    bars = [_bar(trade_date=date(2024, 1, 2)), _bar(trade_date=date(2024, 1, 3))]
    assert find_duplicate_trade_dates(bars) == {}


def test_find_missing_sessions_detects_gap() -> None:
    bars = [_bar(trade_date=date(2024, 1, 2)), _bar(trade_date=date(2024, 1, 4))]
    calendar = [
        RawCalendarDay(date(2024, 1, 2), True, "observed"),
        RawCalendarDay(date(2024, 1, 3), True, "observed"),
        RawCalendarDay(date(2024, 1, 4), True, "observed"),
    ]
    missing = find_missing_sessions(bars, calendar)
    assert missing == [date(2024, 1, 3)]


def test_find_missing_sessions_empty_calendar_is_noop() -> None:
    bars = [_bar(trade_date=date(2024, 1, 2))]
    assert find_missing_sessions(bars, []) == []


def test_is_stale_true_when_gap_exceeds_threshold() -> None:
    assert is_stale(date(2024, 1, 1), as_of=date(2024, 1, 10), max_staleness_days=5) is True


def test_is_stale_false_within_threshold() -> None:
    assert is_stale(date(2024, 1, 8), as_of=date(2024, 1, 10), max_staleness_days=5) is False


def test_is_stale_true_when_no_data() -> None:
    assert is_stale(None, as_of=date(2024, 1, 10)) is True
