"""Observability (MASTER-PRD §20: "Monitor: ... queue depth, worker
health, latency, freshness, error rates"). Deliberately a plain JSON
status endpoint rather than a Prometheus/Grafana stack — proportionate
to this project's personal-use scale, and consistent with using
JobRun (a DB table, same pattern as every other *Run audit table in
this codebase) as the source of truth instead of a separate metrics
system.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from redis import Redis
from rq import Worker
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.enums import JobStatus, JobType
from app.db.models import JobRun
from app.worker.queue import get_queue

RECENT_FAILURE_WINDOW_DAYS = 7
STALE_JOB_THRESHOLD_DAYS = 2  # a stage that hasn't run successfully in this long is flagged


@dataclass(frozen=True, slots=True)
class StageStatus:
    job_type: JobType
    last_status: JobStatus | None
    last_run_date: date | None
    last_finished_at: datetime | None
    is_stale: bool


@dataclass(frozen=True, slots=True)
class OpsStatus:
    queue_depth: int
    worker_count: int
    stages: list[StageStatus]
    recent_failure_count: int


def get_ops_status(session: Session, redis: Redis) -> OpsStatus:
    queue = get_queue(redis)
    queue_depth = len(queue)
    worker_count = len(Worker.all(connection=redis, queue=queue))

    stages: list[StageStatus] = []
    today = datetime.now(UTC).date()
    for job_type in JobType:
        latest = session.scalar(
            select(JobRun)
            .where(JobRun.job_type == job_type)
            .order_by(JobRun.started_at.desc())
            .limit(1)
        )
        if latest is None:
            stages.append(
                StageStatus(
                    job_type=job_type,
                    last_status=None,
                    last_run_date=None,
                    last_finished_at=None,
                    is_stale=True,
                )
            )
            continue
        stale = (today - latest.run_date).days > STALE_JOB_THRESHOLD_DAYS
        stages.append(
            StageStatus(
                job_type=job_type,
                last_status=latest.status,
                last_run_date=latest.run_date,
                last_finished_at=latest.finished_at,
                is_stale=stale,
            )
        )

    window_start = datetime.now(UTC) - timedelta(days=RECENT_FAILURE_WINDOW_DAYS)
    recent_failure_count = (
        session.scalar(
            select(func.count())
            .select_from(JobRun)
            .where(JobRun.status == JobStatus.FAILED, JobRun.started_at >= window_start)
        )
        or 0
    )

    return OpsStatus(
        queue_depth=queue_depth,
        worker_count=worker_count,
        stages=stages,
        recent_failure_count=recent_failure_count,
    )
