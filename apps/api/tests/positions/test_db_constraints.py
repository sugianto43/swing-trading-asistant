import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import ExecutionSide, ListingStatus, PositionStatus
from app.db.models import Execution, Instrument, JournalEntry, Position

T0 = datetime(2024, 1, 1, tzinfo=UTC)


def _instrument() -> Instrument:
    return Instrument(
        symbol=f"T{uuid.uuid4().hex[:8]}",
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol="TEST.JK",
    )


def _position(instrument_id) -> Position:
    return Position(
        instrument_id=instrument_id,
        status=PositionStatus.OPEN,
        quantity_open=100,
        avg_entry_price=1000.0,
        cumulative_quantity_bought=100,
        cumulative_entry_fees=0.0,
        cumulative_exit_fees=0.0,
        realized_pnl=0.0,
        opened_at=T0,
    )


def test_journal_entry_unique_per_position(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()
    position = _position(instrument.id)
    db_session.add(position)
    db_session.commit()

    db_session.add(JournalEntry(position_id=position.id, thesis="a", reference_urls=[]))
    db_session.commit()

    db_session.add(JournalEntry(position_id=position.id, thesis="b", reference_urls=[]))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_execution_allows_multiple_rows_per_position(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()
    position = _position(instrument.id)
    db_session.add(position)
    db_session.commit()

    db_session.add(
        Execution(
            position_id=position.id,
            instrument_id=instrument.id,
            side=ExecutionSide.BUY,
            quantity=50,
            price=1000.0,
            fee=0.0,
            executed_at=T0,
        )
    )
    db_session.add(
        Execution(
            position_id=position.id,
            instrument_id=instrument.id,
            side=ExecutionSide.BUY,
            quantity=50,
            price=1010.0,
            fee=0.0,
            executed_at=T0,
        )
    )
    db_session.commit()  # must not raise — no unique constraint on executions


def test_position_allows_one_terminal_and_one_non_terminal_row(db_session) -> None:
    """A CLOSED position plus a freshly-OPEN position (after reopening)
    for the same instrument is allowed — the partial unique index only
    restricts non-terminal (PLANNED/OPEN/PARTIALLY_CLOSED) rows, so a
    terminal row alongside a non-terminal one is not a violation."""
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    closed = _position(instrument.id)
    closed.status = PositionStatus.CLOSED
    closed.quantity_open = 0
    db_session.add(closed)
    db_session.add(_position(instrument.id))
    db_session.commit()  # must not raise


def test_position_partial_unique_index_blocks_two_non_terminal_rows(db_session) -> None:
    """Regression for the fix-phase HIGH finding: two non-terminal
    (e.g. both OPEN) Position rows for the same instrument must be
    rejected at the DB level, not just by ExecutionService's
    check-then-insert (which a race could slip past silently)."""
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    db_session.add(_position(instrument.id))
    db_session.commit()

    db_session.add(_position(instrument.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
