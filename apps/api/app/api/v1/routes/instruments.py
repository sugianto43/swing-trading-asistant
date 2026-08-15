from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_instrument_or_404
from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.market_data import CorporateActionOut, InstrumentOut, PriceBarOut
from app.db.models import CorporateAction, Instrument, PriceBar
from app.db.session import get_db
from app.marketdata.adjustment import compute_split_adjusted_bars

router = APIRouter()


@router.get("/instruments", response_model=Page[InstrumentOut])
def list_instruments(
    db: Annotated[Session, Depends(get_db)],
    sector: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[InstrumentOut]:
    query = select(Instrument)
    if sector:
        query = query.where(Instrument.sector == sector)
    if status_filter:
        query = query.where(Instrument.status == status_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Instrument.symbol).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[InstrumentOut](
        items=[InstrumentOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/instruments/{symbol}", response_model=InstrumentOut)
def get_instrument(symbol: str, db: Annotated[Session, Depends(get_db)]) -> InstrumentOut:
    instrument = get_instrument_or_404(db, symbol)
    return InstrumentOut.model_validate(instrument)


@router.get("/instruments/{symbol}/prices", response_model=Page[PriceBarOut])
def list_instrument_prices(
    symbol: str,
    db: Annotated[Session, Depends(get_db)],
    start: date | None = None,
    end: date | None = None,
    adjusted: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[PriceBarOut]:
    instrument = get_instrument_or_404(db, symbol)

    query = select(PriceBar).where(PriceBar.instrument_id == instrument.id)
    if start:
        query = query.where(PriceBar.trade_date >= start)
    if end:
        query = query.where(PriceBar.trade_date <= end)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(PriceBar.trade_date.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    if adjusted and rows:
        corporate_actions = db.scalars(
            select(CorporateAction).where(CorporateAction.instrument_id == instrument.id)
        ).all()
        adjusted_by_date = {
            bar.trade_date: bar
            for bar in compute_split_adjusted_bars(list(rows), list(corporate_actions))
        }
        items = []
        for row in rows:
            adjusted_bar = adjusted_by_date.get(row.trade_date)
            item = PriceBarOut.model_validate(row)
            if adjusted_bar:
                item = item.model_copy(
                    update={
                        "open": adjusted_bar.open,
                        "high": adjusted_bar.high,
                        "low": adjusted_bar.low,
                        "close": adjusted_bar.close,
                        "volume": adjusted_bar.volume,
                    }
                )
            items.append(item)
    else:
        items = [PriceBarOut.model_validate(row) for row in rows]

    return Page[PriceBarOut](items=items, page=page, page_size=page_size, total=total)


@router.get("/instruments/{symbol}/corporate-actions", response_model=Page[CorporateActionOut])
def list_instrument_corporate_actions(
    symbol: str,
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[CorporateActionOut]:
    instrument = get_instrument_or_404(db, symbol)
    query = select(CorporateAction).where(CorporateAction.instrument_id == instrument.id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(CorporateAction.ex_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[CorporateActionOut](
        items=[CorporateActionOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
