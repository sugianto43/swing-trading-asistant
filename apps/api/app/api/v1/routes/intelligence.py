from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.intelligence import (
    BreadthComputeRequest,
    BreadthSnapshotOut,
    EventOut,
    SectorPerformanceOut,
)
from app.db.models import BreadthSnapshot, Instrument
from app.db.session import get_db
from app.intelligence.service import MarketIntelligenceService

router = APIRouter()


@router.post("/intelligence/breadth/compute", response_model=BreadthSnapshotOut)
def compute_breadth(
    body: BreadthComputeRequest, db: Annotated[Session, Depends(get_db)]
) -> BreadthSnapshotOut:
    service = MarketIntelligenceService(db)
    snapshot = service.compute_breadth_snapshot(body.as_of)
    return BreadthSnapshotOut.model_validate(snapshot)


@router.get("/intelligence/breadth", response_model=BreadthSnapshotOut)
def get_breadth(
    db: Annotated[Session, Depends(get_db)], as_of: date | None = None
) -> BreadthSnapshotOut:
    service = MarketIntelligenceService(db)
    snapshot = service.get_breadth_snapshot(as_of)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no breadth snapshot available"
        )
    return BreadthSnapshotOut.model_validate(snapshot)


@router.get("/intelligence/breadth/history", response_model=Page[BreadthSnapshotOut])
def list_breadth_history(
    db: Annotated[Session, Depends(get_db)],
    start: date | None = None,
    end: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[BreadthSnapshotOut]:
    query = select(BreadthSnapshot)
    if start is not None:
        query = query.where(BreadthSnapshot.as_of >= start)
    if end is not None:
        query = query.where(BreadthSnapshot.as_of <= end)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(BreadthSnapshot.as_of.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[BreadthSnapshotOut](
        items=[BreadthSnapshotOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/intelligence/sector-performance", response_model=list[SectorPerformanceOut])
def get_sector_performance(
    db: Annotated[Session, Depends(get_db)],
    as_of: date,
    lookback_days: int = Query(default=20, ge=1, le=365),
) -> list[SectorPerformanceOut]:
    service = MarketIntelligenceService(db)
    results = service.sector_performance(as_of, lookback_days)
    return [SectorPerformanceOut(**asdict(r)) for r in results]


@router.get("/intelligence/events", response_model=Page[EventOut])
def list_events(
    db: Annotated[Session, Depends(get_db)],
    symbol: str | None = None,
    as_of: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[EventOut]:
    service = MarketIntelligenceService(db)
    events = service.get_events(symbol=symbol, as_of=as_of)

    instrument_ids = {e.instrument_id for e in events}
    symbol_by_id = {
        i.id: i.symbol
        for i in db.scalars(select(Instrument).where(Instrument.id.in_(instrument_ids))).all()
    }

    total = len(events)
    start_index = (page - 1) * page_size
    page_events = events[start_index : start_index + page_size]

    return Page[EventOut](
        items=[
            EventOut(
                instrument_id=e.instrument_id,
                symbol=symbol_by_id.get(e.instrument_id, "UNKNOWN"),
                event_type=e.event_type,
                announced_at=e.announced_at,
                availability_is_estimated=e.availability_is_estimated,
                ex_date=e.ex_date,
                effective_date=e.effective_date,
                description=e.description,
            )
            for e in page_events
        ],
        page=page,
        page_size=page_size,
        total=total,
    )
