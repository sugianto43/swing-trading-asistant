"""The actual unit of work RQ enqueues/schedules: runs the full daily
pipeline (ingestion -> indicators -> scanner -> risk plans -> breadth ->
alerts) for a symbol universe, one stage at a time, each guarded by a
distributed lock keyed on (job_type, date) so a duplicate/overlapping
enqueue is a safe no-op rather than a double-run (TDD's "duplicate job"
reliability focus). Each stage opens and closes its own DB session,
since an RQ worker process can't share a SQLAlchemy session with
whatever enqueued it.
"""

from collections.abc import Callable
from datetime import date, timedelta

from redis import Redis
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.enums import JobType
from app.db.models import JobRun
from app.db.session import SessionLocal
from app.worker.jobs import (
    run_alerts,
    run_breadth,
    run_indicators,
    run_ingestion,
    run_risk_plans,
    run_scanner,
)
from app.worker.locks import job_lock
from app.worker.queue import get_redis

DEFAULT_INGESTION_LOOKBACK_DAYS = 90


def _run_stage_with_lock(
    redis: Redis, job_type: JobType, run_date: date, fn: Callable[[Session], JobRun]
) -> JobRun | None:
    with job_lock(redis, job_type.value, run_date.isoformat()) as acquired:
        if not acquired:
            return None  # another run already holds this stage+date — safe no-op, not an error
        session = SessionLocal()
        try:
            return fn(session)
        finally:
            session.close()


def enqueue_pipeline(
    symbols: list[str], as_of: date | None = None, redis: Redis | None = None
) -> list[JobRun | None]:
    as_of = as_of or date.today()
    start = as_of - timedelta(days=DEFAULT_INGESTION_LOOKBACK_DAYS)
    redis = redis or get_redis()

    results: list[JobRun | None] = []
    results.append(
        _run_stage_with_lock(
            redis,
            JobType.INGESTION,
            as_of,
            lambda s: run_ingestion(s, symbols, "yfinance", start, as_of, as_of),
        )
    )
    results.append(
        _run_stage_with_lock(
            redis,
            JobType.INDICATORS,
            as_of,
            lambda s: run_indicators(s, symbols, start, as_of, as_of),
        )
    )
    results.append(
        _run_stage_with_lock(
            redis, JobType.SCANNER, as_of, lambda s: run_scanner(s, symbols, as_of, as_of)
        )
    )
    results.append(
        _run_stage_with_lock(
            redis,
            JobType.RISK_PLANS,
            as_of,
            lambda s: run_risk_plans(s, as_of, as_of, get_settings().pipeline_capital),
        )
    )
    results.append(
        _run_stage_with_lock(redis, JobType.BREADTH, as_of, lambda s: run_breadth(s, as_of, as_of))
    )
    results.append(
        _run_stage_with_lock(
            redis, JobType.ALERTS, as_of, lambda s: run_alerts(s, as_of, as_of, redis=redis)
        )
    )
    return results
