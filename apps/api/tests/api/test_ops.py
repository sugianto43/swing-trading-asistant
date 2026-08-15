from datetime import date

import fakeredis

from app.db.enums import JobStatus, JobType
from app.db.models import JobRun
from app.worker.queue import get_redis

RUN_DATE = date(2024, 3, 1)


def _job_run(job_type: JobType, status: JobStatus) -> JobRun:
    return JobRun(job_type=job_type, status=status, run_date=RUN_DATE)


def test_ops_status_returns_stage_summary(client, db_session):
    redis = fakeredis.FakeRedis()
    client.app.dependency_overrides[get_redis] = lambda: redis
    try:
        response = client.get("/api/v1/ops/status")
    finally:
        client.app.dependency_overrides.pop(get_redis, None)

    assert response.status_code == 200
    body = response.json()
    assert body["queue_depth"] == 0
    assert body["worker_count"] == 0
    assert len(body["stages"]) == len(list(JobType))


def test_ops_job_runs_empty(client) -> None:
    response = client.get("/api/v1/ops/job-runs")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_ops_job_runs_returns_persisted_runs(client, db_session) -> None:
    db_session.add(_job_run(JobType.INGESTION, JobStatus.SUCCEEDED))
    db_session.commit()

    response = client.get("/api/v1/ops/job-runs")

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["job_type"] == JobType.INGESTION.value


def test_ops_job_runs_filters_by_job_type(client, db_session) -> None:
    db_session.add(_job_run(JobType.INGESTION, JobStatus.SUCCEEDED))
    db_session.add(_job_run(JobType.SCANNER, JobStatus.FAILED))
    db_session.commit()

    response = client.get("/api/v1/ops/job-runs", params={"job_type": "SCANNER"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["job_type"] == JobType.SCANNER.value


def test_ops_job_runs_filters_by_status(client, db_session) -> None:
    db_session.add(_job_run(JobType.INGESTION, JobStatus.SUCCEEDED))
    db_session.add(_job_run(JobType.SCANNER, JobStatus.FAILED))
    db_session.commit()

    response = client.get("/api/v1/ops/job-runs", params={"status": "FAILED"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == JobStatus.FAILED.value
