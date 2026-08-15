import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.risk import TradePlanCreate, TradePlanOut
from app.db.enums import SetupType, TradePlanStatus
from app.db.models import Instrument, TradePlan
from app.db.session import get_db
from app.risk.engine import PortfolioPosition
from app.risk.service import RiskService

router = APIRouter()


@router.post("/risk/trade-plans", response_model=TradePlanOut, status_code=status.HTTP_201_CREATED)
def create_trade_plan(
    body: TradePlanCreate, db: Annotated[Session, Depends(get_db)]
) -> TradePlanOut:
    service = RiskService(db)
    existing_positions = [
        PortfolioPosition(symbol=p.symbol, sector=p.sector, allocation_amount=p.allocation_amount)
        for p in body.existing_positions
    ]
    try:
        plan = service.build_plan(
            symbol=body.symbol,
            setup_type=body.setup_type,
            plan_date=body.plan_date,
            capital=body.capital,
            existing_positions=existing_positions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return TradePlanOut.model_validate(plan)


@router.get("/risk/trade-plans", response_model=Page[TradePlanOut])
def list_trade_plans(
    db: Annotated[Session, Depends(get_db)],
    symbol: str | None = None,
    setup_type: SetupType | None = None,
    status_filter: Annotated[TradePlanStatus | None, Query(alias="status")] = None,
    plan_date: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[TradePlanOut]:
    query = select(TradePlan)
    if symbol is not None:
        query = query.join(Instrument, TradePlan.instrument_id == Instrument.id).where(
            Instrument.symbol == symbol
        )
    if setup_type is not None:
        query = query.where(TradePlan.setup_type == setup_type)
    if status_filter is not None:
        query = query.where(TradePlan.status == status_filter)
    if plan_date is not None:
        query = query.where(TradePlan.plan_date == plan_date)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(TradePlan.plan_date.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[TradePlanOut](
        items=[TradePlanOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/risk/trade-plans/{trade_plan_id}", response_model=TradePlanOut)
def get_trade_plan(
    trade_plan_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> TradePlanOut:
    plan = db.scalar(select(TradePlan).where(TradePlan.id == trade_plan_id))
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="trade plan not found")
    return TradePlanOut.model_validate(plan)
