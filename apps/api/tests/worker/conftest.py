from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401  registers metadata
from app.db.base import Base
from app.db.enums import DataQualityStatus, ListingStatus, SetupType
from app.db.models import (
    IndicatorSnapshot,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
    ScanCandidate,
)
from app.indicators.versioning import INDICATOR_VERSION
from app.scanner.scoring_config import SCORE_VERSION


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def seed_instrument(db_session, symbol: str = "BBCA", sector: str | None = "Banking") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        sector=sector,
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.flush()
    db_session.add(
        InstrumentStatusHistory(
            instrument_id=instrument.id,
            status=ListingStatus.ACTIVE,
            effective_from=datetime(2020, 1, 1, tzinfo=UTC),
            source="fixture",
        )
    )
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def seed_price_and_indicator(
    db_session, instrument: Instrument, as_of: date, days: int = 5
) -> None:
    for i in range(days):
        trade_date = as_of - timedelta(days=days - 1 - i)
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=1000.0,
                high=1010.0,
                low=990.0,
                close=1000.0,
                volume=1_000_000,
                source="fixture",
                source_symbol=instrument.source_symbol,
                quality_status=DataQualityStatus.VALID,
            )
        )
        db_session.add(
            IndicatorSnapshot(
                instrument_id=instrument.id,
                trade_date=trade_date,
                indicator_version=INDICATOR_VERSION,
                atr_14=20.0,
                volume_sma_20=1_000_000.0,
                relative_volume=1.0,
            )
        )
    db_session.commit()


def seed_scan_candidate(
    db_session, instrument: Instrument, scan_date: date, setup_type: SetupType = SetupType.BREAKOUT
) -> ScanCandidate:
    candidate = ScanCandidate(
        instrument_id=instrument.id,
        scan_date=scan_date,
        setup_type=setup_type,
        indicator_version=INDICATOR_VERSION,
        score_version=SCORE_VERSION,
        composite_score=80.0,
        trend_score=0,
        momentum_score=0,
        volume_score=0,
        price_structure_score=0,
        volatility_score=0,
        setup_quality_score=0,
        risk_reward_score=0,
        qualifying_conditions=["test"],
        invalidation_conditions=["close below breakout level"],
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate
