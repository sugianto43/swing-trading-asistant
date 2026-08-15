import uuid
from datetime import UTC, date, datetime

from app.backtesting.universe import is_active_as_of
from app.db.enums import ListingStatus
from app.db.models import Instrument, InstrumentStatusHistory


def _instrument(listing_date: date | None = None, delisting_date: date | None = None) -> Instrument:
    return Instrument(
        id=uuid.uuid4(),
        symbol="TEST",
        company_name="Test Co",
        source="fixture",
        source_symbol="TEST.JK",
        listing_date=listing_date,
        delisting_date=delisting_date,
    )


def _status(status: ListingStatus, effective_from: datetime) -> InstrumentStatusHistory:
    return InstrumentStatusHistory(
        instrument_id=uuid.uuid4(), status=status, effective_from=effective_from, source="fixture"
    )


def test_no_history_but_within_listing_window_defaults_eligible() -> None:
    # This is the exact scenario that was previously (wrongly) excluded:
    # InstrumentStatusHistory rows are stamped at ingestion wall-clock
    # time, so a backtest over historical dates predating ingestion would
    # never have an "applicable" history row. The listing_date/
    # delisting_date window is the authoritative baseline instead.
    instrument = _instrument(listing_date=date(2020, 1, 1))
    assert is_active_as_of(instrument, [], date(2023, 9, 18)) is True


def test_before_listing_date_is_not_eligible() -> None:
    instrument = _instrument(listing_date=date(2024, 6, 1))
    assert is_active_as_of(instrument, [], date(2024, 1, 1)) is False


def test_boundary_exactly_on_listing_date_is_eligible() -> None:
    instrument = _instrument(listing_date=date(2024, 6, 1))
    assert is_active_as_of(instrument, [], date(2024, 6, 1)) is True


def test_after_delisting_date_is_not_eligible() -> None:
    instrument = _instrument(listing_date=date(2020, 1, 1), delisting_date=date(2024, 6, 1))
    assert is_active_as_of(instrument, [], date(2024, 12, 1)) is False


def test_boundary_exactly_on_delisting_date_is_eligible() -> None:
    instrument = _instrument(listing_date=date(2020, 1, 1), delisting_date=date(2024, 6, 1))
    assert is_active_as_of(instrument, [], date(2024, 6, 1)) is True


def test_no_listing_date_at_all_defaults_eligible() -> None:
    instrument = _instrument(listing_date=None, delisting_date=None)
    assert is_active_as_of(instrument, [], date(2020, 1, 1)) is True


def test_status_history_overrides_baseline_for_observed_suspension() -> None:
    instrument = _instrument(listing_date=date(2020, 1, 1))
    history = [_status(ListingStatus.SUSPENDED, datetime(2024, 1, 1, tzinfo=UTC))]
    # within the listing window but a later-observed suspension applies
    assert is_active_as_of(instrument, history, date(2024, 6, 1)) is False


def test_status_history_reinstatement_after_suspension() -> None:
    instrument = _instrument(listing_date=date(2020, 1, 1))
    history = [
        _status(ListingStatus.SUSPENDED, datetime(2024, 1, 1, tzinfo=UTC)),
        _status(ListingStatus.ACTIVE, datetime(2024, 5, 1, tzinfo=UTC)),
    ]
    assert is_active_as_of(instrument, history, date(2024, 3, 1)) is False  # during suspension
    assert is_active_as_of(instrument, history, date(2024, 6, 1)) is True  # reinstated


def test_status_history_not_applicable_before_its_own_effective_date() -> None:
    # a history row dated after `as_of` must not apply retroactively
    instrument = _instrument(listing_date=date(2020, 1, 1))
    history = [_status(ListingStatus.SUSPENDED, datetime(2024, 6, 1, tzinfo=UTC))]
    assert is_active_as_of(instrument, history, date(2024, 1, 1)) is True
