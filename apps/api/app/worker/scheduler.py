"""Registers `enqueue_pipeline` itself as a single daily cron-triggered RQ
job (via rq-scheduler). All six pipeline stages run sequentially inside
that one job invocation, not as separate RQ jobs — a whole-job retry (see
`app.worker.queue.DEFAULT_RETRY`) re-runs the entire pipeline from
ingestion, not just the stage that failed. Per-stage inspection/history is
still available via each stage's own `JobRun` row, but per-stage retry
granularity would require enqueueing each stage as its own RQ job with
`depends_on` chaining instead — not done here (rq-scheduler's `cron()`
also has no `retry=` parameter, so retries for the cron-scheduled path
rely on RQ's default no-retry behavior; only the CLI's manual
`enqueue-pipeline` path currently gets `DEFAULT_RETRY`).
"""

from redis import Redis
from rq_scheduler import Scheduler

from app.worker.pipeline import enqueue_pipeline
from app.worker.queue import get_queue

DAILY_CRON = "30 09 * * 1-5"  # 09:30 UTC = 16:30 WIB (no DST in Indonesia), Mon-Fri — after IDX
# close (15:00-16:00 WIB). rq-scheduler evaluates cron against the process's
# system clock, which is UTC in the deployed containers (no TZ set) — this
# must stay expressed in UTC, not WIB, or it silently fires ~7 hours late.


def register_daily_pipeline(redis: Redis, symbols: list[str]) -> None:
    scheduler = Scheduler(queue=get_queue(redis), connection=redis)
    # clear any previously-registered instance of this job before
    # re-registering, so restarting the scheduler process never creates
    # duplicate cron entries for the same job.
    for job in scheduler.get_jobs():
        if job.func_name == f"{enqueue_pipeline.__module__}.{enqueue_pipeline.__name__}":
            scheduler.cancel(job)

    scheduler.cron(
        DAILY_CRON,
        func=enqueue_pipeline,
        args=[symbols],
        queue_name=get_queue(redis).name,
    )
