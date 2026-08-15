from datetime import UTC, date, datetime, timedelta

import fakeredis

from app.db.enums import JobStatus, JobType
from app.db.models import JobRun
from app.worker.ops_service import STALE_JOB_THRESHOLD_DAYS, get_ops_status
from app.worker.queue import get_queue

TODAY = datetime.now(UTC).date()


def _job_run(job_type: JobType, status: JobStatus, run_date: date, started_at: datetime) -> JobRun:
    return JobRun(
        job_type=job_type,
        status=status,
        run_date=run_date,
        started_at=started_at,
        finished_at=started_at,
    )


def test_get_ops_status_empty_db_marks_every_stage_stale(db_session) -> None:
    redis = fakeredis.FakeRedis()

    status = get_ops_status(db_session, redis)

    assert status.queue_depth == 0
    assert status.worker_count == 0
    assert status.recent_failure_count == 0
    assert len(status.stages) == len(list(JobType))
    assert all(s.is_stale for s in status.stages)
    assert all(s.last_status is None for s in status.stages)


def test_get_ops_status_recent_run_is_not_stale(db_session) -> None:
    redis = fakeredis.FakeRedis()
    db_session.add(_job_run(JobType.INGESTION, JobStatus.SUCCEEDED, TODAY, datetime.now(UTC)))
    db_session.commit()

    status = get_ops_status(db_session, redis)

    ingestion = next(s for s in status.stages if s.job_type == JobType.INGESTION)
    assert ingestion.is_stale is False
    assert ingestion.last_status == JobStatus.SUCCEEDED


def test_get_ops_status_old_run_is_stale(db_session) -> None:
    redis = fakeredis.FakeRedis()
    old_date = TODAY - timedelta(days=STALE_JOB_THRESHOLD_DAYS + 1)
    db_session.add(
        _job_run(
            JobType.SCANNER,
            JobStatus.SUCCEEDED,
            old_date,
            datetime.now(UTC) - timedelta(days=STALE_JOB_THRESHOLD_DAYS + 1),
        )
    )
    db_session.commit()

    status = get_ops_status(db_session, redis)

    scanner = next(s for s in status.stages if s.job_type == JobType.SCANNER)
    assert scanner.is_stale is True


def test_get_ops_status_counts_recent_failures_only(db_session) -> None:
    redis = fakeredis.FakeRedis()
    db_session.add(_job_run(JobType.INGESTION, JobStatus.FAILED, TODAY, datetime.now(UTC)))
    db_session.add(
        _job_run(
            JobType.INDICATORS,
            JobStatus.FAILED,
            TODAY - timedelta(days=30),
            datetime.now(UTC) - timedelta(days=30),
        )
    )
    db_session.commit()

    status = get_ops_status(db_session, redis)

    assert status.recent_failure_count == 1


def test_get_ops_status_reflects_queue_depth(db_session) -> None:
    redis = fakeredis.FakeRedis()
    queue = get_queue(redis)
    queue.enqueue(len, [1, 2, 3])

    status = get_ops_status(db_session, redis)

    assert status.queue_depth == 1
