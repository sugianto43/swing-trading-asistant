from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import ListingStatus
from app.db.models import IndicatorSnapshot, Instrument


def test_duplicate_indicator_snapshot_violates_unique_constraint(db_session) -> None:
    instrument = Instrument(
        symbol="BBCA",
        company_name="Bank Central Asia Tbk",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol="BBCA.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)

    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id, trade_date=date(2024, 1, 2), indicator_version="v1"
        )
    )
    db_session.commit()

    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id, trade_date=date(2024, 1, 2), indicator_version="v1"
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
