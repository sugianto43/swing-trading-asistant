from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_instrument_or_404
from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.indicators import IndicatorSnapshotOut
from app.db.models import IndicatorSnapshot
from app.db.session import get_db
from app.indicators.versioning import INDICATOR_VERSION

router = APIRouter()


@router.get("/instruments/{symbol}/indicators", response_model=Page[IndicatorSnapshotOut])
def list_instrument_indicators(
    symbol: str,
    db: Annotated[Session, Depends(get_db)],
    start: date | None = None,
    end: date | None = None,
    indicator_version: str = INDICATOR_VERSION,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[IndicatorSnapshotOut]:
    instrument = get_instrument_or_404(db, symbol)

    query = select(IndicatorSnapshot).where(
        IndicatorSnapshot.instrument_id == instrument.id,
        IndicatorSnapshot.indicator_version == indicator_version,
    )
    if start:
        query = query.where(IndicatorSnapshot.trade_date >= start)
    if end:
        query = query.where(IndicatorSnapshot.trade_date <= end)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(IndicatorSnapshot.trade_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[IndicatorSnapshotOut](
        items=[IndicatorSnapshotOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
