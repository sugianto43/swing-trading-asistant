import uuid
from datetime import UTC, datetime

import pytest

from app.db.enums import ExecutionSide, ListingStatus
from app.db.models import Instrument
from app.positions.execution_service import ExecutionService
from app.positions.journal_service import JournalService

T0 = datetime(2024, 1, 1, tzinfo=UTC)


def _seed_position(db_session):
    instrument = Instrument(
        symbol="BBCA",
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol="BBCA.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    return ExecutionService(db_session).record_execution(
        symbol="BBCA", side=ExecutionSide.BUY, quantity=100, price=1000.0, fee=0.0, executed_at=T0
    )


def test_upsert_journal_creates_entry(db_session) -> None:
    position = _seed_position(db_session)
    service = JournalService(db_session)

    entry = service.upsert_journal(
        position.id, thesis="breakout above resistance", mistakes=None, lessons=None
    )
    assert entry.position_id == position.id
    assert entry.thesis == "breakout above resistance"
    assert entry.reference_urls == []


def test_upsert_journal_updates_existing_entry_not_duplicate(db_session) -> None:
    position = _seed_position(db_session)
    service = JournalService(db_session)

    first = service.upsert_journal(position.id, thesis="v1")
    second = service.upsert_journal(position.id, thesis="v2", lessons="patience")

    assert first.id == second.id
    assert second.thesis == "v2"
    assert second.lessons == "patience"


def test_upsert_journal_with_reference_urls(db_session) -> None:
    position = _seed_position(db_session)
    service = JournalService(db_session)
    entry = service.upsert_journal(position.id, reference_urls=["https://example.com/chart.png"])
    assert entry.reference_urls == ["https://example.com/chart.png"]


def test_upsert_journal_unknown_position_raises(db_session) -> None:
    service = JournalService(db_session)
    with pytest.raises(ValueError, match="not found"):
        service.upsert_journal(uuid.uuid4(), thesis="x")


def test_get_journal_returns_none_when_absent(db_session) -> None:
    position = _seed_position(db_session)
    service = JournalService(db_session)
    assert service.get_journal(position.id) is None


def test_get_journal_returns_entry(db_session) -> None:
    position = _seed_position(db_session)
    service = JournalService(db_session)
    service.upsert_journal(position.id, thesis="x")
    entry = service.get_journal(position.id)
    assert entry is not None
    assert entry.thesis == "x"
