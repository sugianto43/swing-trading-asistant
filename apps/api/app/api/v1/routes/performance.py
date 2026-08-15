from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.schemas.performance import (
    BehaviorEntryOut,
    GroupPerformanceOut,
    PerformanceSummaryOut,
)
from app.db.session import get_db
from app.positions.performance_service import PerformanceService

router = APIRouter()


@router.get("/performance/summary", response_model=PerformanceSummaryOut)
def get_performance_summary(
    db: Annotated[Session, Depends(get_db)],
    initial_capital: float = Query(default=0.0, ge=0),
) -> PerformanceSummaryOut:
    summary = PerformanceService(db).summary(initial_capital=initial_capital)
    return PerformanceSummaryOut(**asdict(summary))


@router.get("/performance/by-setup", response_model=list[GroupPerformanceOut])
def get_performance_by_setup(db: Annotated[Session, Depends(get_db)]) -> list[GroupPerformanceOut]:
    return [GroupPerformanceOut(**asdict(g)) for g in PerformanceService(db).by_setup()]


@router.get("/performance/by-sector", response_model=list[GroupPerformanceOut])
def get_performance_by_sector(db: Annotated[Session, Depends(get_db)]) -> list[GroupPerformanceOut]:
    return [GroupPerformanceOut(**asdict(g)) for g in PerformanceService(db).by_sector()]


@router.get("/performance/by-holding-period", response_model=list[GroupPerformanceOut])
def get_performance_by_holding_period(
    db: Annotated[Session, Depends(get_db)],
) -> list[GroupPerformanceOut]:
    return [GroupPerformanceOut(**asdict(g)) for g in PerformanceService(db).by_holding_period()]


@router.get("/performance/by-score-bucket", response_model=list[GroupPerformanceOut])
def get_performance_by_score_bucket(
    db: Annotated[Session, Depends(get_db)],
) -> list[GroupPerformanceOut]:
    return [GroupPerformanceOut(**asdict(g)) for g in PerformanceService(db).by_score_bucket()]


@router.get("/performance/behavior", response_model=list[BehaviorEntryOut])
def get_performance_behavior(db: Annotated[Session, Depends(get_db)]) -> list[BehaviorEntryOut]:
    return [
        BehaviorEntryOut(**{**asdict(b), "position_id": str(b.position_id)})
        for b in PerformanceService(db).behavior()
    ]
