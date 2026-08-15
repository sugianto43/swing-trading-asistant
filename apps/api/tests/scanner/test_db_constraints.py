from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import ListingStatus, SetupType
from app.db.models import Instrument, ScanCandidate

# Bypasses ScannerService's upsert-by-natural-key logic and inserts
# directly via the ORM, to prove the physical DB constraint is the real
# backstop against duplicate candidates — not just application logic that
# could regress silently (same pattern as Phases 2 and 3).


def _seed_instrument(db_session) -> Instrument:
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
    return instrument


def _candidate(instrument, **overrides) -> ScanCandidate:
    defaults = {
        "instrument_id": instrument.id,
        "scan_date": date(2024, 6, 1),
        "setup_type": SetupType.MOMENTUM_CONTINUATION,
        "indicator_version": "v1",
        "score_version": "v1",
        "composite_score": 75.0,
        "trend_score": 80.0,
        "momentum_score": 70.0,
        "volume_score": 60.0,
        "price_structure_score": 65.0,
        "volatility_score": 90.0,
        "setup_quality_score": 70.0,
        "risk_reward_score": 50.0,
        "qualifying_conditions": ["x"],
        "invalidation_conditions": ["y"],
    }
    defaults.update(overrides)
    return ScanCandidate(**defaults)


def test_duplicate_scan_candidate_violates_unique_constraint(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(_candidate(instrument))
    db_session.commit()

    db_session.add(_candidate(instrument, composite_score=999.0))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_different_setup_type_same_date_is_allowed(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(_candidate(instrument, setup_type=SetupType.MOMENTUM_CONTINUATION))
    db_session.add(_candidate(instrument, setup_type=SetupType.BREAKOUT))
    db_session.commit()  # must not raise — different setup_type, different identity


def test_different_score_version_same_setup_is_allowed(db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(_candidate(instrument, score_version="v1"))
    db_session.add(_candidate(instrument, score_version="v2-experimental"))
    db_session.commit()  # must not raise — different score_version, different identity
