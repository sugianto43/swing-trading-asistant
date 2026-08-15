from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_instrument_or_404
from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.scanner import ScanCandidateOut
from app.db.enums import SetupType
from app.db.models import Instrument, ScanCandidate
from app.db.session import get_db
from app.scanner.scoring_config import SCORE_VERSION

router = APIRouter()


def _to_schema(candidate: ScanCandidate, symbol: str) -> ScanCandidateOut:
    return ScanCandidateOut(
        symbol=symbol,
        scan_date=candidate.scan_date,
        setup_type=candidate.setup_type,
        indicator_version=candidate.indicator_version,
        score_version=candidate.score_version,
        composite_score=candidate.composite_score,
        trend_score=candidate.trend_score,
        momentum_score=candidate.momentum_score,
        volume_score=candidate.volume_score,
        price_structure_score=candidate.price_structure_score,
        volatility_score=candidate.volatility_score,
        setup_quality_score=candidate.setup_quality_score,
        risk_reward_score=candidate.risk_reward_score,
        qualifying_conditions=candidate.qualifying_conditions,
        invalidation_conditions=candidate.invalidation_conditions,
    )


_SORT_FIELDS = {
    "score": ScanCandidate.composite_score,
    "momentum": ScanCandidate.momentum_score,
    "risk_reward": ScanCandidate.risk_reward_score,
    # ScanCandidate persists volume_score (a 0-100 ranking transform of
    # relative_volume, capped at 100), not the raw relative_volume value —
    # the sort key name is honest about what it actually orders by.
    "volume_score": ScanCandidate.volume_score,
}


@router.get("/scanner/candidates", response_model=Page[ScanCandidateOut])
def list_scan_candidates(
    db: Annotated[Session, Depends(get_db)],
    sector: str | None = None,
    setup: SetupType | None = None,
    min_score: float | None = None,
    scan_date: date | None = None,
    score_version: str = SCORE_VERSION,
    sort: str = Query(default="score", pattern="^(score|momentum|risk_reward|volume_score)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[ScanCandidateOut]:
    query = (
        select(ScanCandidate, Instrument.symbol)
        .join(Instrument, ScanCandidate.instrument_id == Instrument.id)
        .where(ScanCandidate.score_version == score_version)
    )
    if sector:
        query = query.where(Instrument.sector == sector)
    if setup:
        query = query.where(ScanCandidate.setup_type == setup)
    if min_score is not None:
        query = query.where(ScanCandidate.composite_score >= min_score)
    if scan_date:
        query = query.where(ScanCandidate.scan_date == scan_date)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_column = _SORT_FIELDS[sort]
    rows = db.execute(
        query.order_by(sort_column.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    return Page[ScanCandidateOut](
        items=[_to_schema(candidate, symbol) for candidate, symbol in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/instruments/{symbol}/candidates", response_model=Page[ScanCandidateOut])
def list_instrument_candidates(
    symbol: str,
    db: Annotated[Session, Depends(get_db)],
    score_version: str = SCORE_VERSION,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[ScanCandidateOut]:
    instrument = get_instrument_or_404(db, symbol)
    query = select(ScanCandidate).where(
        ScanCandidate.instrument_id == instrument.id,
        ScanCandidate.score_version == score_version,
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ScanCandidate.scan_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return Page[ScanCandidateOut](
        items=[_to_schema(row, instrument.symbol) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
