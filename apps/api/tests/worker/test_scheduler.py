import fakeredis
from rq_scheduler import Scheduler

from app.worker.pipeline import enqueue_pipeline
from app.worker.queue import get_queue
from app.worker.scheduler import DAILY_CRON, register_daily_pipeline


def _enqueue_pipeline_jobs(redis):
    scheduler = Scheduler(queue=get_queue(redis), connection=redis)
    target_name = f"{enqueue_pipeline.__module__}.{enqueue_pipeline.__name__}"
    return [job for job in scheduler.get_jobs() if job.func_name == target_name]


def test_register_daily_pipeline_creates_one_cron_job() -> None:
    redis = fakeredis.FakeRedis()
    register_daily_pipeline(redis, ["BBCA", "TLKM"])

    jobs = _enqueue_pipeline_jobs(redis)
    assert len(jobs) == 1
    assert jobs[0].meta.get("cron_string") == DAILY_CRON


def test_register_daily_pipeline_passes_symbols_as_args() -> None:
    redis = fakeredis.FakeRedis()
    register_daily_pipeline(redis, ["BBCA", "TLKM"])

    jobs = _enqueue_pipeline_jobs(redis)
    assert jobs[0].args == [["BBCA", "TLKM"]]


def test_register_daily_pipeline_is_idempotent_on_reregister() -> None:
    """Regression target: restarting the scheduler process must not create
    duplicate cron entries for the same job."""
    redis = fakeredis.FakeRedis()
    register_daily_pipeline(redis, ["BBCA"])
    register_daily_pipeline(redis, ["BBCA", "TLKM"])

    jobs = _enqueue_pipeline_jobs(redis)
    assert len(jobs) == 1
    assert jobs[0].args == [["BBCA", "TLKM"]]
