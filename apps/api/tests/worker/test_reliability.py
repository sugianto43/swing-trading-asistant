"""Adversarial tests for TDD's named reliability focuses not otherwise
covered by test_jobs.py/test_locks.py/test_pipeline.py: Redis outage and
DB outage specifically. Documents actual behavior — including one gap
(run_risk_plans) — rather than asserting a fix that hasn't been applied.
"""

import uuid
from datetime import date

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.db.enums import AlertType, JobStatus
from app.db.models import Alert
from app.worker.alert_engine import AlertCandidate
from app.worker.alert_service import AlertService
from app.worker.jobs import run_risk_plans
from app.worker.locks import job_lock
from app.worker.pipeline import enqueue_pipeline
from tests.worker.conftest import seed_instrument, seed_price_and_indicator, seed_scan_candidate

AS_OF = date(2024, 3, 1)


class _BrokenLockRedis:
    """Stands in for a Redis client whose connection is down: any lock
    operation raises redis.exceptions.ConnectionError, same as a real
    redis-py client would when it can't reach the server."""

    def lock(self, *args, **kwargs):
        class _BrokenLock:
            def acquire(self):
                raise RedisConnectionError("Redis is unreachable")

        return _BrokenLock()


def test_job_lock_redis_outage_propagates_not_silently_skipped() -> None:
    """A lock acquisition failure due to Redis being down must raise, not
    be swallowed and treated as 'acquired' — proceeding as if the lock was
    held with no real Redis backing it would defeat the whole duplicate-job
    guarantee."""
    with pytest.raises(RedisConnectionError):
        with job_lock(_BrokenLockRedis(), "INGESTION", "2024-01-01"):
            pass


def test_enqueue_pipeline_redis_outage_fails_fast(monkeypatch) -> None:
    """When Redis itself is unreachable, enqueue_pipeline cannot safely run
    any stage (no locking is possible), so it must fail fast rather than
    silently proceeding without duplicate-job protection."""
    calls: list = []
    import app.worker.pipeline as pipeline_module

    monkeypatch.setattr(
        pipeline_module, "run_ingestion", lambda *a, **kw: calls.append("ingestion")
    )

    with pytest.raises(RedisConnectionError):
        enqueue_pipeline(["BBCA"], as_of=AS_OF, redis=_BrokenLockRedis())

    assert calls == []  # no stage ran without a working lock


class _BrokenPublishRedis:
    """Redis client that connects fine for everything except publish —
    simulates Redis going down between the app's start and the moment a
    freshly-persisted alert is broadcast."""

    def publish(self, channel, payload):
        raise RedisConnectionError("Redis is unreachable")


def test_alert_service_publish_failure_does_not_abort_persistence(db_session) -> None:
    """Regression test for the review-phase finding: a Redis outage at
    publish time must not roll back the already-committed alert, and must
    not prevent persist_alerts from processing the rest of the batch or
    returning normally — broadcast is best-effort, persistence is the
    source of truth."""
    service = AlertService(db_session, redis=_BrokenPublishRedis())
    candidates = [
        AlertCandidate(
            alert_type=AlertType.SETUP_DETECTED,
            instrument_id=uuid.uuid4(),
            message="BBCA: setup detected",
            details={},
        ),
        AlertCandidate(
            alert_type=AlertType.UNUSUAL_VOLUME,
            instrument_id=uuid.uuid4(),
            message="TLKM: unusual volume",
            details={},
        ),
    ]

    persisted = service.persist_alerts(candidates, AS_OF)

    assert len(persisted) == 2
    all_alerts = db_session.scalars(select(Alert)).all()
    assert len(all_alerts) == 2


class _RaiseOnceThenSucceed:
    """Wraps a real bound method so the first call raises (simulating a
    transient DB outage) and subsequent calls behave normally."""

    def __init__(self, original):
        self._original = original
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise OperationalError("SELECT 1", {}, Exception("database is unreachable"))
        return self._original(*args, **kwargs)


def test_run_risk_plans_db_outage_marks_job_failed_not_stuck_running(
    db_session, monkeypatch
) -> None:
    """Regression test for the review-phase finding: unlike
    run_scanner/run_breadth/run_alerts, run_risk_plans used to have no
    top-level try/except around its initial DB reads, so a DB outage
    there propagated uncaught and left the JobRun permanently stuck in
    RUNNING. It's now wrapped the same way as the other five job
    functions — a DB outage during the initial reads must mark the
    JobRun FAILED, not leave it stuck."""
    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF)
    seed_scan_candidate(db_session, instrument, AS_OF)

    monkeypatch.setattr(db_session, "scalars", _RaiseOnceThenSucceed(db_session.scalars))

    job = run_risk_plans(db_session, AS_OF, AS_OF, capital=100_000_000.0)

    assert job.status == JobStatus.FAILED
    assert job.finished_at is not None
    assert job.error_message is not None and "database is unreachable" in job.error_message
