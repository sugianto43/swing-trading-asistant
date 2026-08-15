import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import JobStatus, JobType


class StageStatusOut(BaseModel):
    job_type: JobType
    last_status: JobStatus | None
    last_run_date: date | None
    last_finished_at: datetime | None
    is_stale: bool


class OpsStatusOut(BaseModel):
    queue_depth: int
    worker_count: int
    stages: list[StageStatusOut]
    recent_failure_count: int


class JobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: JobType
    run_date: date
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
