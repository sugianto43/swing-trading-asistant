import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.orchestrator import AIAnalystService
from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.ai import AnalysisSnapshotOut, AnalyzeRequest
from app.db.models import AnalysisSnapshot, Instrument
from app.db.session import get_db

router = APIRouter()


@router.post("/ai/analyze", response_model=AnalysisSnapshotOut, status_code=status.HTTP_201_CREATED)
def analyze(body: AnalyzeRequest, db: Annotated[Session, Depends(get_db)]) -> AnalysisSnapshotOut:
    service = AIAnalystService(db)
    try:
        snapshot = service.analyze(question=body.question, symbol=body.symbol)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return AnalysisSnapshotOut.model_validate(snapshot)


@router.get("/ai/snapshots", response_model=Page[AnalysisSnapshotOut])
def list_snapshots(
    db: Annotated[Session, Depends(get_db)],
    symbol: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[AnalysisSnapshotOut]:
    query = select(AnalysisSnapshot)
    if symbol is not None:
        query = query.join(Instrument, AnalysisSnapshot.instrument_id == Instrument.id).where(
            Instrument.symbol == symbol
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(AnalysisSnapshot.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page[AnalysisSnapshotOut](
        items=[AnalysisSnapshotOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/ai/snapshots/{snapshot_id}", response_model=AnalysisSnapshotOut)
def get_snapshot(
    snapshot_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> AnalysisSnapshotOut:
    snapshot = db.scalar(select(AnalysisSnapshot).where(AnalysisSnapshot.id == snapshot_id))
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot not found")
    return AnalysisSnapshotOut.model_validate(snapshot)
