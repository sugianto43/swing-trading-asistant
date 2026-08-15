"""Canonicalizes existing CorporateAction rows (Phase 2) into a
timestamped Event shape for market-intelligence consumption — a
read-time projection, not a new ingestion path or a duplicated table.
No new data is invented; every field traces back to an already-ingested
CorporateAction.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from app.db.models import CorporateAction


@dataclass(frozen=True, slots=True)
class Event:
    instrument_id: uuid.UUID
    event_type: str
    announced_at: datetime
    availability_is_estimated: bool
    ex_date: date
    effective_date: date | None
    description: str


def corporate_action_to_event(ca: CorporateAction) -> Event:
    """`announced_at` is the field any 'what was knowable as of date X'
    query must filter on (QUANT-TRADING-RULES.md: publication timestamp,
    never ex_date/effective_date, which can be scheduled/known in
    advance of when the action actually took public-availability
    effect). yfinance doesn't always supply an announcement timestamp —
    when `ca.announced_at` is null, `ca.ingested_at` (when this system
    first learned about it) is used as a conservative fallback, and
    `availability_is_estimated=True` flags that substitution explicitly
    rather than silently presenting a fallback as if it were the real
    announcement time.
    """
    announced_at = ca.announced_at if ca.announced_at is not None else ca.ingested_at
    availability_is_estimated = ca.announced_at is None

    parts = [ca.action_type.value]
    if ca.ratio is not None:
        parts.append(f"ratio={float(ca.ratio)}")
    if ca.amount is not None:
        parts.append(f"amount={float(ca.amount)}")
    description = " ".join(parts)

    return Event(
        instrument_id=ca.instrument_id,
        event_type=ca.action_type.value,
        announced_at=announced_at,
        availability_is_estimated=availability_is_estimated,
        ex_date=ca.ex_date,
        effective_date=ca.effective_date,
        description=description,
    )
