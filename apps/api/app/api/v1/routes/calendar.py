from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.market_data import CalendarDayOut
from app.db.models import TradingCalendarDay
from app.db.session import get_db

router = APIRouter()


@router.get("/calendar", response_model=Page[CalendarDayOut])
def list_calendar_days(
    db: Annotated[Session, Depends(get_db)],
    start: date | None = None,
    end: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[CalendarDayOut]:
    query = select(TradingCalendarDay)
    if start:
        query = query.where(TradingCalendarDay.date >= start)
    if end:
        query = query.where(TradingCalendarDay.date <= end)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(TradingCalendarDay.date).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[CalendarDayOut](
        items=[CalendarDayOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
