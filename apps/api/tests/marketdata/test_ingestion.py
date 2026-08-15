from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.enums import CorporateActionType, DataQualityStatus, IngestionStatus, ListingStatus
from app.db.models import (
    CorporateAction,
    IngestionRun,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
)
from app.marketdata.fixture_provider import FixtureProvider
from app.marketdata.ingestion import IngestionService
from app.marketdata.provider import RawBar, RawCorporateAction, RawInstrument


def _minimal_instrument(symbol: str = "BBCA", source_symbol: str = "BBCA.JK") -> RawInstrument:
    return RawInstrument(
        symbol=symbol,
        source_symbol=source_symbol,
        company_name="Bank Central Asia Tbk",
        source="fixture",
    )


def test_sync_instruments_creates_and_records_status_history(db_session) -> None:
    provider = FixtureProvider(instruments=[_minimal_instrument()])
    service = IngestionService(db_session, provider)

    result = service.sync_instruments()

    assert result == {"created": 1, "updated": 0}
    instrument = db_session.scalar(select(Instrument).where(Instrument.symbol == "BBCA"))
    assert instrument is not None
    history = db_session.scalars(
        select(InstrumentStatusHistory).where(
            InstrumentStatusHistory.instrument_id == instrument.id
        )
    ).all()
    assert len(history) == 1
    assert history[0].status == ListingStatus.ACTIVE


def test_sync_instruments_is_idempotent(db_session) -> None:
    provider = FixtureProvider(instruments=[_minimal_instrument()])
    service = IngestionService(db_session, provider)

    service.sync_instruments()
    result = service.sync_instruments()

    assert result == {"created": 0, "updated": 1}
    assert db_session.scalar(select(Instrument)) is not None
    count = len(db_session.scalars(select(Instrument)).all())
    assert count == 1


def test_sync_instruments_records_status_change(db_session) -> None:
    provider = FixtureProvider(instruments=[_minimal_instrument()])
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    suspended = FixtureProvider(
        instruments=[
            RawInstrument(
                symbol="BBCA",
                source_symbol="BBCA.JK",
                company_name="Bank Central Asia Tbk",
                source="fixture",
                status=ListingStatus.SUSPENDED,
            )
        ]
    )
    IngestionService(db_session, suspended).sync_instruments()

    instrument = db_session.scalar(select(Instrument).where(Instrument.symbol == "BBCA"))
    assert instrument.status == ListingStatus.SUSPENDED
    history = db_session.scalars(
        select(InstrumentStatusHistory).where(
            InstrumentStatusHistory.instrument_id == instrument.id
        )
    ).all()
    assert len(history) == 2


def test_ingest_prices_requires_instrument_to_be_seeded(db_session) -> None:
    provider = FixtureProvider(bars={})
    service = IngestionService(db_session, provider)

    with pytest.raises(ValueError, match="not seeded"):
        service.ingest_prices("BBCA", date(2024, 1, 1), date(2024, 1, 31))


def test_ingest_prices_persists_valid_bars(db_session) -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, 8950, 9050, 1_000_000, "fixture"),
            RawBar("BBCA.JK", date(2024, 1, 3), 9050, 9200, 9000, 9150, 1_200_000, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    summary = service.ingest_prices(
        "BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5)
    )

    assert summary.records_processed == 2
    assert summary.records_flagged == 0
    persisted = db_session.scalars(select(PriceBar)).all()
    assert len(persisted) == 2
    assert all(bar.quality_status == DataQualityStatus.VALID for bar in persisted)


def test_ingest_prices_marks_invalid_bar_without_dropping_it(db_session) -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, -50, 9050, 1_000_000, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    summary = service.ingest_prices(
        "BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5)
    )

    assert summary.records_processed == 1
    assert summary.records_flagged == 1
    persisted = db_session.scalar(select(PriceBar))
    assert persisted is not None  # never dropped
    assert persisted.quality_status == DataQualityStatus.INVALID
    assert "NON_POSITIVE_PRICE" in persisted.quality_notes


def test_ingest_prices_rejects_future_dated_bar_as_leakage_guard(db_session) -> None:
    as_of = date(2024, 1, 5)
    bars = {
        "BBCA.JK": [
            RawBar(
                "BBCA.JK", as_of + timedelta(days=3), 9000, 9100, 8950, 9050, 1_000_000, "fixture"
            ),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    summary = service.ingest_prices("BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=as_of)

    persisted = db_session.scalar(select(PriceBar))
    assert persisted.quality_status == DataQualityStatus.INVALID
    assert "FUTURE_DATED_BAR" in persisted.quality_notes
    assert summary.records_flagged == 1


def test_ingest_prices_deduplicates_provider_side_duplicates(db_session) -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, 8950, 9050, 1_000_000, "fixture"),
            RawBar("BBCA.JK", date(2024, 1, 2), 9999, 9999, 9999, 9999, 1, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    summary = service.ingest_prices(
        "BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5)
    )

    assert summary.records_processed == 1
    assert "duplicate trade dates" in summary.notes[0]
    persisted = db_session.scalar(select(PriceBar))
    assert persisted.close == 9050  # first occurrence kept deterministically


def test_ingest_prices_is_idempotent_on_rerun(db_session) -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, 8950, 9050, 1_000_000, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    service.ingest_prices("BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5))
    service.ingest_prices("BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5))

    assert len(db_session.scalars(select(PriceBar)).all()) == 1


def test_ingest_prices_is_reproducible(db_session) -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, 8950, 9050, 1_000_000, "fixture"),
            RawBar("BBCA.JK", date(2024, 1, 3), 9050, 9200, 9000, 9150, 1_200_000, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    first = service.ingest_prices(
        "BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5)
    )
    second = service.ingest_prices(
        "BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5)
    )

    assert first.records_processed == second.records_processed
    assert first.records_flagged == second.records_flagged
    persisted = db_session.scalars(select(PriceBar).order_by(PriceBar.trade_date)).all()
    assert [(b.trade_date, float(b.close)) for b in persisted] == [
        (date(2024, 1, 2), 9050.0),
        (date(2024, 1, 3), 9150.0),
    ]


def test_ingest_corporate_actions_persists_and_is_idempotent(db_session) -> None:
    actions = {
        "BBCA.JK": [
            RawCorporateAction(
                "BBCA.JK",
                CorporateActionType.CASH_DIVIDEND,
                date(2024, 3, 1),
                "fixture",
                amount=50.0,
            ),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], corporate_actions=actions)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    service.ingest_corporate_actions("BBCA", date(2024, 1, 1), date(2024, 12, 31))
    summary = service.ingest_corporate_actions("BBCA", date(2024, 1, 1), date(2024, 12, 31))

    assert summary.records_processed == 1
    persisted = db_session.scalars(select(CorporateAction)).all()
    assert len(persisted) == 1
    assert float(persisted[0].amount) == 50.0


def test_ingest_corporate_actions_rejects_future_dated_as_leakage_guard(db_session) -> None:
    as_of = date(2024, 1, 5)
    actions = {
        "BBCA.JK": [
            RawCorporateAction(
                "BBCA.JK",
                CorporateActionType.CASH_DIVIDEND,
                as_of + timedelta(days=30),
                "fixture",
                amount=50.0,
            ),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], corporate_actions=actions)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    summary = service.ingest_corporate_actions(
        "BBCA", date(2024, 1, 1), date(2024, 12, 31), as_of=as_of
    )

    assert summary.records_processed == 0
    assert summary.records_flagged == 1
    assert summary.status.value == "PARTIAL"
    assert "skipped" in summary.notes[0]
    assert db_session.scalars(select(CorporateAction)).all() == []


def test_ingest_corporate_actions_rejects_non_positive_ratio(db_session) -> None:
    actions = {
        "BBCA.JK": [
            RawCorporateAction(
                "BBCA.JK", CorporateActionType.SPLIT, date(2024, 3, 1), "fixture", ratio=-1.0
            ),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], corporate_actions=actions)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    summary = service.ingest_corporate_actions(
        "BBCA", date(2024, 1, 1), date(2024, 12, 31), as_of=date(2025, 1, 1)
    )

    assert summary.records_processed == 0
    assert summary.records_flagged == 1
    assert db_session.scalars(select(CorporateAction)).all() == []


def test_ingest_corporate_actions_preserves_distinct_timestamp_fields(db_session) -> None:
    # ex_date, effective_date, and announced_at must remain independently
    # traceable (QUANT-TRADING-RULES: publication vs effective vs event date).
    announced = datetime(2024, 2, 1, 8, 0, tzinfo=UTC)
    actions = {
        "BBCA.JK": [
            RawCorporateAction(
                "BBCA.JK",
                CorporateActionType.CASH_DIVIDEND,
                ex_date=date(2024, 3, 1),
                source="fixture",
                effective_date=date(2024, 3, 5),
                announced_at=announced,
                amount=50.0,
            ),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], corporate_actions=actions)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    service.ingest_corporate_actions(
        "BBCA", date(2024, 1, 1), date(2024, 12, 31), as_of=date(2025, 1, 1)
    )

    persisted = db_session.scalar(select(CorporateAction))
    assert persisted.ex_date == date(2024, 3, 1)
    assert persisted.effective_date == date(2024, 3, 5)
    # sqlite drops tzinfo on DateTime(timezone=True); compare naive here,
    # Postgres (used in CI's migration job and production) preserves it.
    assert persisted.announced_at.replace(tzinfo=UTC) == announced
    assert len({persisted.ex_date, persisted.effective_date, persisted.announced_at.date()}) == 3


def test_ingest_prices_stale_data_is_flagged_in_notes(db_session) -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, 8950, 9050, 1_000_000, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    # as_of is 30 days after the only bar — well past the default staleness
    # threshold (MASTER-PRD §20: stale data must not silently pass as fresh).
    summary = service.ingest_prices(
        "BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 2, 1)
    )

    assert any("stale" in note for note in summary.notes)


class _BrokenProvider:
    """Provider whose get_daily_bars/get_corporate_actions always raise, to
    exercise the IngestionRun FAILED path (nothing else can trigger it)."""

    name = "broken"

    def get_instruments(self):
        return [_minimal_instrument()]

    def get_daily_bars(self, source_symbol, start, end):
        raise RuntimeError("simulated provider outage")

    def get_corporate_actions(self, source_symbol, start, end):
        raise RuntimeError("simulated provider outage")

    def get_calendar(self, start, end):
        return []

    def get_latest_quote(self, source_symbol):
        return None


def test_ingest_prices_marks_run_failed_on_provider_error(db_session) -> None:
    provider = _BrokenProvider()
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    with pytest.raises(RuntimeError, match="simulated provider outage"):
        service.ingest_prices("BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5))

    run = db_session.scalar(select(IngestionRun))
    assert run is not None
    assert run.status == IngestionStatus.FAILED
    assert run.error_message == "simulated provider outage"
    assert run.finished_at is not None


def test_ingest_corporate_actions_marks_run_failed_on_provider_error(db_session) -> None:
    provider = _BrokenProvider()
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    with pytest.raises(RuntimeError, match="simulated provider outage"):
        service.ingest_corporate_actions(
            "BBCA", date(2024, 1, 1), date(2024, 12, 31), as_of=date(2024, 1, 5)
        )

    run = db_session.scalar(select(IngestionRun))
    assert run is not None
    assert run.status == IngestionStatus.FAILED
    assert run.error_message == "simulated provider outage"


def test_ingest_prices_fully_invalid_batch_is_partial_not_succeeded(db_session) -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, -50, 9050, 1_000_000, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    summary = service.ingest_prices(
        "BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5)
    )

    # every bar was flagged INVALID — status must not read as a clean success
    assert summary.records_processed == summary.records_flagged == 1
    assert summary.status.value == "PARTIAL"


def test_ingest_prices_abnormal_volume_baseline_excludes_invalid_bar(db_session) -> None:
    bars = {
        "BBCA.JK": [
            # day 1: invalid (non-positive price) but a huge volume number
            RawBar("BBCA.JK", date(2024, 1, 2), 9000, 9100, 0, 9050, 50_000_000, "fixture"),
            # day 2: perfectly normal volume relative to a *real* prior day,
            # but would look "abnormal" only if compared against day 1's
            # inflated volume
            RawBar("BBCA.JK", date(2024, 1, 3), 9050, 9200, 9000, 9150, 1_000_000, "fixture"),
        ]
    }
    provider = FixtureProvider(instruments=[_minimal_instrument()], bars=bars)
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    service.ingest_prices("BBCA", date(2024, 1, 1), date(2024, 1, 31), as_of=date(2024, 1, 5))

    day2 = db_session.scalar(select(PriceBar).where(PriceBar.trade_date == date(2024, 1, 3)))
    assert day2.quality_status == DataQualityStatus.VALID
    assert not day2.quality_notes


def test_historical_universe_membership_queryable_as_of_date(db_session) -> None:
    provider = FixtureProvider(instruments=[_minimal_instrument()])
    service = IngestionService(db_session, provider)
    service.sync_instruments()

    instrument = db_session.scalar(select(Instrument).where(Instrument.symbol == "BBCA"))
    first_effective_from = db_session.scalar(
        select(InstrumentStatusHistory.effective_from).where(
            InstrumentStatusHistory.instrument_id == instrument.id
        )
    )

    suspended = FixtureProvider(
        instruments=[
            RawInstrument(
                symbol="BBCA",
                source_symbol="BBCA.JK",
                company_name="Bank Central Asia Tbk",
                source="fixture",
                status=ListingStatus.SUSPENDED,
            )
        ]
    )
    IngestionService(db_session, suspended).sync_instruments()

    # "as of" the first ingestion, the instrument was ACTIVE — reconstructing
    # universe membership at a past timestamp must not see the later change.
    status_as_of_first_ingestion = db_session.scalars(
        select(InstrumentStatusHistory)
        .where(
            InstrumentStatusHistory.instrument_id == instrument.id,
            InstrumentStatusHistory.effective_from <= first_effective_from,
        )
        .order_by(InstrumentStatusHistory.effective_from.desc())
    ).first()
    assert status_as_of_first_ingestion.status == ListingStatus.ACTIVE

    # "as of" now, the instrument reflects the later suspension.
    current_status = db_session.scalar(select(Instrument).where(Instrument.symbol == "BBCA")).status
    assert current_status == ListingStatus.SUSPENDED
