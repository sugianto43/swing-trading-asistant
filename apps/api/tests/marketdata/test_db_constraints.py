from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import CorporateActionType
from app.db.models import CorporateAction, Instrument, PriceBar

# These tests bypass IngestionService's upsert-by-natural-key logic and
# insert directly via the ORM, to prove the physical DB constraint is the
# real backstop against duplicate rows — not just application-level logic
# that could regress silently.


def _seed_instrument(db_session) -> Instrument:
    instrument = Instrument(
        symbol="BBCA",
        company_name="Bank Central Asia Tbk",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        source="fixture",
        source_symbol="BBCA.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def test_duplicate_price_bar_violates_unique_constraint(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=date(2024, 1, 2),
            open=100,
            high=105,
            low=95,
            close=102,
            volume=1000,
            source="fixture",
            source_symbol="BBCA.JK",
        )
    )
    db_session.commit()

    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=date(2024, 1, 2),
            open=999,
            high=999,
            low=999,
            close=999,
            volume=1,
            source="fixture",
            source_symbol="BBCA.JK",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_corporate_action_violates_unique_constraint(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date=date(2024, 3, 1),
            source="fixture",
            source_symbol="BBCA.JK",
            amount=50.0,
        )
    )
    db_session.commit()

    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date=date(2024, 3, 1),
            source="fixture",
            source_symbol="BBCA.JK",
            amount=999.0,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_duplicate_instrument_symbol_violates_unique_constraint(db_session) -> None:
    db_session.add(
        Instrument(
            symbol="BBCA",
            company_name="Bank Central Asia Tbk",
            exchange="IDX",
            currency="IDR",
            security_type="EQUITY",
            source="fixture",
            source_symbol="BBCA.JK",
        )
    )
    db_session.commit()

    db_session.add(
        Instrument(
            symbol="BBCA",
            company_name="Duplicate",
            exchange="IDX",
            currency="IDR",
            security_type="EQUITY",
            source="fixture",
            source_symbol="BBCA2.JK",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
