import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import JournalEntry, Position


class JournalService:
    """Ordinary create-or-update CRUD for the one journal entry per
    position — unlike ExecutionService, journal entries are meant to be
    edited as the trader's reflection evolves, so there's no append-only
    constraint here."""

    def __init__(self, session: Session):
        self.session = session

    def upsert_journal(
        self,
        position_id: uuid.UUID,
        *,
        thesis: str | None = None,
        market_context: str | None = None,
        execution_quality: str | None = None,
        behavioral_notes: str | None = None,
        plan_adherence_notes: str | None = None,
        mistakes: str | None = None,
        lessons: str | None = None,
        reference_urls: list[str] | None = None,
    ) -> JournalEntry:
        position = self.session.scalar(select(Position).where(Position.id == position_id))
        if position is None:
            raise ValueError(f"position not found: {position_id}")

        values = {
            "thesis": thesis,
            "market_context": market_context,
            "execution_quality": execution_quality,
            "behavioral_notes": behavioral_notes,
            "plan_adherence_notes": plan_adherence_notes,
            "mistakes": mistakes,
            "lessons": lessons,
            "reference_urls": reference_urls or [],
        }

        existing = self.session.scalar(
            select(JournalEntry).where(JournalEntry.position_id == position_id)
        )
        if existing is None:
            entry = JournalEntry(position_id=position_id, **values)
            self.session.add(entry)
        else:
            for field, value in values.items():
                setattr(existing, field, value)
            entry = existing
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def get_journal(self, position_id: uuid.UUID) -> JournalEntry | None:
        return self.session.scalar(
            select(JournalEntry).where(JournalEntry.position_id == position_id)
        )
