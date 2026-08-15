from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import MarketRegime
from app.db.models import BreadthSnapshot

T0 = date(2024, 3, 1)


def _snapshot(**overrides) -> BreadthSnapshot:
    defaults = dict(
        as_of=T0,
        breadth_version="v1",
        universe_size=10,
        pct_above_sma50=0.6,
        pct_above_sma200=0.5,
        advancers=6,
        decliners=4,
        unchanged=0,
        new_highs_20=1,
        new_lows_20=0,
        regime=MarketRegime.RISK_ON,
        regime_version="v1",
    )
    defaults.update(overrides)
    return BreadthSnapshot(**defaults)


def test_duplicate_natural_key_violates_unique_constraint(db_session) -> None:
    db_session.add(_snapshot())
    db_session.commit()

    db_session.add(_snapshot())
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_different_breadth_version_same_date_is_allowed(db_session) -> None:
    db_session.add(_snapshot(breadth_version="v1"))
    db_session.add(_snapshot(breadth_version="v2"))
    db_session.commit()  # must not raise


def test_different_date_same_version_is_allowed(db_session) -> None:
    db_session.add(_snapshot(as_of=T0))
    db_session.add(_snapshot(as_of=date(2024, 3, 2)))
    db_session.commit()  # must not raise


def test_nullable_pct_fields_round_trip(db_session) -> None:
    snapshot = _snapshot(pct_above_sma50=None, pct_above_sma200=None)
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    assert snapshot.pct_above_sma50 is None
    assert snapshot.pct_above_sma200 is None
