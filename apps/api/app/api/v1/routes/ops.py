from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.ops import JobRunOut, OpsStatusOut, StageStatusOut
from app.db.enums import JobStatus, JobType
from app.db.models import JobRun
from app.db.session import get_db
from app.worker.ops_service import get_ops_status
from app.worker.queue import get_redis

router = APIRouter()


@router.get("/ops/status", response_model=OpsStatusOut)
def ops_status(
    db: Annotated[Session, Depends(get_db)], redis: Annotated[Redis, Depends(get_redis)]
) -> OpsStatusOut:
    status = get_ops_status(db, redis)
    return OpsStatusOut(
        queue_depth=status.queue_depth,
        worker_count=status.worker_count,
        stages=[StageStatusOut(**asdict(s)) for s in status.stages],
        recent_failure_count=status.recent_failure_count,
    )


@router.get("/ops/job-runs", response_model=Page[JobRunOut])
def list_job_runs(
    db: Annotated[Session, Depends(get_db)],
    job_type: JobType | None = None,
    status_filter: Annotated[JobStatus | None, Query(alias="status")] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[JobRunOut]:
    query = select(JobRun)
    if job_type is not None:
        query = query.where(JobRun.job_type == job_type)
    if status_filter is not None:
        query = query.where(JobRun.status == status_filter)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(JobRun.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[JobRunOut](
        items=[JobRunOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
