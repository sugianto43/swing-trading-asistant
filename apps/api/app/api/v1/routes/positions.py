import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.positions import (
    ExecutionCreate,
    ExecutionOut,
    JournalOut,
    JournalUpsert,
    PlannedPositionCreate,
    PositionOut,
)
from app.db.enums import PositionStatus
from app.db.models import Execution, Instrument, Position
from app.db.session import get_db
from app.positions.execution_service import ExecutionService
from app.positions.journal_service import JournalService

router = APIRouter()


def _raise_from_value_error(exc: ValueError) -> None:
    # "not found" messages map to 404; every other ValueError from the
    # position/execution services describes an invalid state transition
    # given current data (overselling, wrong status for the action,
    # etc.) — a 409 conflict, not a 422 payload-shape error.
    message = str(exc)
    if "not found" in message or "not seeded" in message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc


@router.post("/executions", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
def record_execution(body: ExecutionCreate, db: Annotated[Session, Depends(get_db)]) -> PositionOut:
    service = ExecutionService(db)
    try:
        position = service.record_execution(
            symbol=body.symbol,
            side=body.side,
            quantity=body.quantity,
            price=body.price,
            fee=body.fee,
            executed_at=body.executed_at,
            trade_plan_id=body.trade_plan_id,
            notes=body.notes,
        )
    except ValueError as exc:
        _raise_from_value_error(exc)
        raise  # unreachable, satisfies type checker
    return PositionOut.model_validate(position)


@router.get("/executions", response_model=Page[ExecutionOut])
def list_executions(
    db: Annotated[Session, Depends(get_db)],
    symbol: str | None = None,
    position_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[ExecutionOut]:
    query = select(Execution)
    if symbol is not None:
        query = query.join(Instrument, Execution.instrument_id == Instrument.id).where(
            Instrument.symbol == symbol
        )
    if position_id is not None:
        query = query.where(Execution.position_id == position_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Execution.executed_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[ExecutionOut](
        items=[ExecutionOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/positions", response_model=PositionOut, status_code=status.HTTP_201_CREATED)
def create_planned_position(
    body: PlannedPositionCreate, db: Annotated[Session, Depends(get_db)]
) -> PositionOut:
    service = ExecutionService(db)
    try:
        position = service.create_planned_position(body.trade_plan_id)
    except ValueError as exc:
        _raise_from_value_error(exc)
        raise
    return PositionOut.model_validate(position)


@router.post("/positions/{position_id}/cancel", response_model=PositionOut)
def cancel_position(position_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> PositionOut:
    service = ExecutionService(db)
    try:
        position = service.cancel_position(position_id)
    except ValueError as exc:
        _raise_from_value_error(exc)
        raise
    return PositionOut.model_validate(position)


@router.get("/positions", response_model=Page[PositionOut])
def list_positions(
    db: Annotated[Session, Depends(get_db)],
    symbol: str | None = None,
    status_filter: Annotated[PositionStatus | None, Query(alias="status")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[PositionOut]:
    query = select(Position)
    if symbol is not None:
        query = query.join(Instrument, Position.instrument_id == Instrument.id).where(
            Instrument.symbol == symbol
        )
    if status_filter is not None:
        query = query.where(Position.status == status_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Position.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[PositionOut](
        items=[PositionOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/positions/{position_id}", response_model=PositionOut)
def get_position(position_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> PositionOut:
    position = db.scalar(select(Position).where(Position.id == position_id))
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="position not found")
    return PositionOut.model_validate(position)


@router.post("/positions/{position_id}/journal", response_model=JournalOut)
def upsert_journal(
    position_id: uuid.UUID, body: JournalUpsert, db: Annotated[Session, Depends(get_db)]
) -> JournalOut:
    service = JournalService(db)
    try:
        entry = service.upsert_journal(position_id, **body.model_dump())
    except ValueError as exc:
        _raise_from_value_error(exc)
        raise
    return JournalOut.model_validate(entry)


@router.get("/positions/{position_id}/journal", response_model=JournalOut)
def get_journal(position_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> JournalOut:
    service = JournalService(db)
    entry = service.get_journal(position_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="journal entry not found")
    return JournalOut.model_validate(entry)
