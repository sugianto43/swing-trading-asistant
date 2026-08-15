from datetime import date

from app.db.enums import ListingStatus
from app.db.models import Instrument, InstrumentStatusHistory


def is_active_as_of(
    instrument: Instrument, history: list[InstrumentStatusHistory], as_of: date
) -> bool:
    """Point-in-time survivorship check: was this instrument ACTIVE as of
    `as_of`?

    `InstrumentStatusHistory.effective_from` is stamped at the wall-clock
    time a status change was OBSERVED by this system (Phase 2's
    `sync_instruments`) — for an instrument ingested today, every history
    row is dated today, regardless of the historical date being
    backtested. Relying on it alone would make every pre-ingestion
    historical date look "not yet listed" and silently exclude every
    instrument from every backtest.

    So `instrument.listing_date`/`delisting_date` (the actual exchange
    dates, from the seed/vendor data) are the authoritative baseline for
    dates before this system started tracking. `InstrumentStatusHistory`
    only refines that baseline for dates where it has an applicable
    observation (e.g. a suspension detected during live operation) — it
    is a correction on top of the baseline, not a replacement for it.
    """
    if instrument.listing_date is not None and as_of < instrument.listing_date:
        return False
    if instrument.delisting_date is not None and as_of > instrument.delisting_date:
        return False

    applicable = [h for h in history if h.effective_from.date() <= as_of]
    if not applicable:
        return True  # within the listing window, no observed status change yet — default eligible

    latest = max(applicable, key=lambda h: h.effective_from)
    return latest.status == ListingStatus.ACTIVE
