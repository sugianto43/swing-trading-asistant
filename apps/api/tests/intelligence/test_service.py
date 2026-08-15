from datetime import UTC, date, datetime, timedelta

import pytest

from app.db.enums import CorporateActionType, DataQualityStatus, ListingStatus
from app.db.models import BreadthSnapshot, CorporateAction, IndicatorSnapshot, Instrument, PriceBar
from app.intelligence.service import MarketIntelligenceService

T0 = date(2024, 3, 1)


def _seed_instrument(
    db_session, symbol="BBCA", sector="Banking", listing_date=None, delisting_date=None
) -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        sector=sector,
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
        listing_date=listing_date,
        delisting_date=delisting_date,
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_price_and_indicator(
    db_session,
    instrument,
    trade_date,
    close,
    prior_close=None,
    sma_50=None,
    sma_200=None,
    rolling_high_20=None,
    rolling_low_20=None,
):
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    if prior_close is not None:
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date - timedelta(days=1),
                open=prior_close,
                high=prior_close,
                low=prior_close,
                close=prior_close,
                volume=1_000_000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id,
            trade_date=trade_date,
            indicator_version="v1",
            sma_50=sma_50,
            sma_200=sma_200,
            rolling_high_20=rolling_high_20,
            rolling_low_20=rolling_low_20,
        )
    )
    db_session.commit()


def test_compute_breadth_snapshot_persists_and_is_idempotent(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(
        db_session, instrument, T0, close=110, prior_close=100, sma_50=100, sma_200=90
    )

    service = MarketIntelligenceService(db_session)
    first = service.compute_breadth_snapshot(T0)
    assert first.universe_size == 1
    assert first.pct_above_sma50 == 1.0

    second = service.compute_breadth_snapshot(T0)
    assert first.id == second.id  # same row updated, not duplicated

    all_snapshots = db_session.query(BreadthSnapshot).count()
    assert all_snapshots == 1


def test_compute_breadth_snapshot_excludes_delisted_instrument(db_session) -> None:
    """Survivorship: an instrument delisted before as_of must not
    contribute to the breadth snapshot for that date."""
    active = _seed_instrument(db_session, symbol="BBCA", listing_date=date(2020, 1, 1))
    delisted = _seed_instrument(
        db_session,
        symbol="DELISTED",
        listing_date=date(2020, 1, 1),
        delisting_date=date(2024, 1, 1),  # delisted before T0
    )
    _seed_price_and_indicator(db_session, active, T0, close=110, sma_50=100)
    _seed_price_and_indicator(db_session, delisted, T0, close=110, sma_50=100)

    service = MarketIntelligenceService(db_session)
    snapshot = service.compute_breadth_snapshot(T0)
    assert snapshot.universe_size == 1  # only the still-active instrument counted


def test_compute_breadth_snapshot_excludes_instrument_missing_exact_date_data(db_session) -> None:
    """An instrument whose latest indicator snapshot is from a different
    (older) date must be excluded, never silently reused as if it were
    today's data."""
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, T0 - timedelta(days=5), close=100, sma_50=90)
    # no data exactly on T0

    service = MarketIntelligenceService(db_session)
    snapshot = service.compute_breadth_snapshot(T0)
    assert snapshot.universe_size == 0


def test_no_look_ahead_future_mutation_does_not_change_past_snapshot(db_session) -> None:
    """Adversarial: mutating/adding data dated AFTER as_of must not
    change a breadth snapshot already computed for an earlier date."""
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, T0, close=110, prior_close=100, sma_50=100)
    service = MarketIntelligenceService(db_session)
    baseline = service.compute_breadth_snapshot(T0)
    baseline_pct = baseline.pct_above_sma50

    # add wildly different future data
    future_instrument = _seed_instrument(db_session, symbol="FUTURE")
    _seed_price_and_indicator(
        db_session, future_instrument, T0 + timedelta(days=5), close=9999, sma_50=1
    )

    # recompute for the SAME as_of date — must be unaffected by future data
    replay = service.compute_breadth_snapshot(T0)
    assert replay.pct_above_sma50 == baseline_pct
    assert replay.universe_size == baseline.universe_size


def test_get_breadth_snapshot_latest_when_no_as_of_given(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, T0, close=100, sma_50=90)
    _seed_price_and_indicator(db_session, instrument, T0 + timedelta(days=1), close=105, sma_50=90)
    service = MarketIntelligenceService(db_session)
    service.compute_breadth_snapshot(T0)
    service.compute_breadth_snapshot(T0 + timedelta(days=1))

    latest = service.get_breadth_snapshot()
    assert latest.as_of == T0 + timedelta(days=1)


def test_get_breadth_snapshot_returns_none_when_empty(db_session) -> None:
    service = MarketIntelligenceService(db_session)
    assert service.get_breadth_snapshot() is None


def test_sector_performance_computes_return_over_window(db_session) -> None:
    instrument = _seed_instrument(db_session, sector="Banking")
    _seed_price_and_indicator(db_session, instrument, T0 - timedelta(days=20), close=100)
    _seed_price_and_indicator(db_session, instrument, T0, close=110)

    service = MarketIntelligenceService(db_session)
    results = service.sector_performance(T0, lookback_days=20)
    assert len(results) == 1
    assert results[0].sector == "Banking"
    assert results[0].avg_return_pct == pytest.approx(10.0, rel=0.05)


def test_sector_performance_uses_price_closest_to_window_start_not_oldest_buffer_bar(
    db_session,
) -> None:
    """Regression for the fix-phase HIGH finding: with daily bars spanning
    the whole fetch buffer, sector_performance must use the price closest
    to (at or before) window_start — not the oldest bar in the entire
    buffer, which the bug silently substituted."""
    instrument = _seed_instrument(db_session, sector="Banking")
    # 41 consecutive daily bars, price rising by 1/day: T0-40 -> 100, T0 -> 140
    for i in range(41):
        d = T0 - timedelta(days=40 - i)
        price = 100 + i
        _seed_price_and_indicator(db_session, instrument, d, close=price)

    service = MarketIntelligenceService(db_session)
    results = service.sector_performance(T0, lookback_days=20)
    assert len(results) == 1
    # correct: price 20 days ago (T0-20 -> 120) vs today (T0 -> 140) = 16.67%
    # buggy behavior gave 27.27% (used the T0-30 price of 110 instead)
    assert results[0].avg_return_pct == pytest.approx(16.6667, rel=0.01)


def test_get_breadth_snapshot_pinned_to_current_breadth_version(db_session) -> None:
    """Regression for the fix-phase MEDIUM finding: a stale/different
    breadth_version row for the same as_of must never be returned instead
    of the current version's row."""
    from app.db.enums import MarketRegime
    from app.db.models import BreadthSnapshot
    from app.intelligence.config import BREADTH_VERSION

    db_session.add(
        BreadthSnapshot(
            as_of=T0,
            breadth_version="v0-legacy",
            universe_size=1,
            pct_above_sma50=0.1,
            pct_above_sma200=0.1,
            advancers=1,
            decliners=0,
            unchanged=0,
            new_highs_20=0,
            new_lows_20=0,
            regime=MarketRegime.RISK_OFF,
            regime_version="v0-legacy",
        )
    )
    db_session.commit()

    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, T0, close=110, sma_50=100)
    service = MarketIntelligenceService(db_session)
    current = service.compute_breadth_snapshot(T0)
    assert current.breadth_version == BREADTH_VERSION

    fetched = service.get_breadth_snapshot(T0)
    assert fetched is not None
    assert fetched.breadth_version == BREADTH_VERSION
    assert fetched.id == current.id


def test_get_events_availability_leakage_excludes_future_announcement(db_session) -> None:
    """Adversarial (TDD Critical Rule): a corporate action announced
    AFTER as_of must never appear in an events query for that as_of,
    even if its ex_date is on or before as_of."""
    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=T0,  # ex_date is ON as_of
            announced_at=datetime(2024, 3, 5, tzinfo=UTC),  # but announced AFTER as_of
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.commit()

    service = MarketIntelligenceService(db_session)
    events = service.get_events(symbol="BBCA", as_of=T0)
    assert events == []  # not yet publicly known as of T0

    events_later = service.get_events(symbol="BBCA", as_of=date(2024, 3, 10))
    assert len(events_later) == 1


def test_get_events_unknown_symbol_returns_empty(db_session) -> None:
    service = MarketIntelligenceService(db_session)
    assert service.get_events(symbol="NOPE", as_of=None) == []


def test_get_events_sorted_most_recent_first(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=date(2024, 1, 1),
            announced_at=datetime(2024, 1, 1, tzinfo=UTC),
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date=date(2024, 6, 1),
            announced_at=datetime(2024, 6, 1, tzinfo=UTC),
            amount=100.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.commit()

    service = MarketIntelligenceService(db_session)
    events = service.get_events(symbol="BBCA", as_of=None)
    assert len(events) == 2
    assert events[0].event_type == "CASH_DIVIDEND"  # most recent first


def test_get_events_boundary_announced_exactly_on_as_of_is_included(db_session) -> None:
    """Inclusive boundary: an event announced exactly on as_of (not
    strictly before) must be considered publicly known as of that date."""
    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=T0,
            announced_at=datetime(2024, 3, 1, 9, 0, tzinfo=UTC),  # same date as as_of
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.commit()

    service = MarketIntelligenceService(db_session)
    events = service.get_events(symbol="BBCA", as_of=T0)
    assert len(events) == 1


def test_event_deduplication_db_constraint_prevents_duplicate_corporate_action(db_session) -> None:
    """Event dedup (TDD focus) is guaranteed upstream by Phase 2's unique
    constraint on (instrument_id, action_type, ex_date, source) — a
    corporate action can never be double-ingested, so get_events can
    never surface the same action twice."""
    from sqlalchemy.exc import IntegrityError

    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=T0,
            announced_at=datetime(2024, 2, 1, tzinfo=UTC),
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.commit()

    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=T0,
            announced_at=datetime(2024, 2, 1, tzinfo=UTC),
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    service = MarketIntelligenceService(db_session)
    events = service.get_events(symbol="BBCA", as_of=None)
    assert len(events) == 1


def test_compute_breadth_snapshot_empty_universe_no_instruments_at_all(db_session) -> None:
    service = MarketIntelligenceService(db_session)
    snapshot = service.compute_breadth_snapshot(T0)
    assert snapshot.universe_size == 0
    assert snapshot.pct_above_sma50 is None
    assert snapshot.regime.value == "NEUTRAL"


def test_compute_breadth_snapshot_reproducible_identical_values_on_recompute(db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(
        db_session, instrument, T0, close=110, prior_close=100, sma_50=100, sma_200=90
    )
    service = MarketIntelligenceService(db_session)
    first = service.compute_breadth_snapshot(T0)
    first_values = (
        first.universe_size,
        float(first.pct_above_sma50),
        first.advancers,
        first.decliners,
        first.regime,
    )

    second = service.compute_breadth_snapshot(T0)
    second_values = (
        second.universe_size,
        float(second.pct_above_sma50),
        second.advancers,
        second.decliners,
        second.regime,
    )
    assert first_values == second_values
