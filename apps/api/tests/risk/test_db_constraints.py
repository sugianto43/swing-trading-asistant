import uuid
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import ListingStatus, SetupType, TradePlanStatus
from app.db.models import Instrument, TradePlan

PLAN_DATE = date(2024, 3, 1)


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


def _plan(instrument_id, **overrides) -> TradePlan:
    defaults = {
        "instrument_id": instrument_id,
        "setup_type": SetupType.BREAKOUT,
        "plan_date": PLAN_DATE,
        "risk_version": "v1",
        "status": TradePlanStatus.VALID,
        "rejection_reasons": [],
        "target_prices": [1050.0, 1090.0],
        "quantity": 100,
        "allocation_amount": 100_000.0,
        "allocation_pct": 0.1,
        "max_loss_amount": 3_000.0,
        "assumptions": {"capital": 1_000_000.0},
        "invalidation_conditions": [],
    }
    defaults.update(overrides)
    return TradePlan(**defaults)


def test_duplicate_natural_key_violates_unique_constraint(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    db_session.add(_plan(instrument.id))
    db_session.commit()

    db_session.add(_plan(instrument.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_different_risk_version_same_day_is_allowed(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    db_session.add(_plan(instrument.id, risk_version="v1"))
    db_session.add(_plan(instrument.id, risk_version="v2"))
    db_session.commit()  # must not raise — different risk_version


def test_different_setup_type_same_day_is_allowed(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    db_session.add(_plan(instrument.id, setup_type=SetupType.BREAKOUT))
    db_session.add(_plan(instrument.id, setup_type=SetupType.MOMENTUM_CONTINUATION))
    db_session.commit()  # must not raise — different setup_type


def test_json_fields_round_trip(db_session) -> None:
    instrument = _instrument()
    db_session.add(instrument)
    db_session.flush()

    plan = _plan(
        instrument.id,
        rejection_reasons=["stop price must be below entry price"],
        target_prices=[1050.5, 1090.25],
        invalidation_conditions=["close below breakout level"],
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    assert plan.rejection_reasons == ["stop price must be below entry price"]
    assert plan.target_prices == [1050.5, 1090.25]
    assert plan.invalidation_conditions == ["close below breakout level"]
