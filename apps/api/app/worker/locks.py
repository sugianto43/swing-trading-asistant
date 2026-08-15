"""Distributed locking (TDD: "distributed locks", targets the
"duplicate job" reliability test) — prevents two workers/schedulers
from concurrently running the same pipeline stage for the same date.
Built on redis-py's own `Lock` primitive (token-based ownership, TTL)
rather than a hand-rolled SETNX, since that's already correct and
well-tested.
"""

from collections.abc import Generator
from contextlib import contextmanager

from redis import Redis
from redis.exceptions import LockError

DEFAULT_LOCK_TTL_SECONDS = 3600  # generous — long enough for a full pipeline stage to finish


def _lock_key(job_type: str, run_date: str) -> str:
    return f"lock:{job_type}:{run_date}"


@contextmanager
def job_lock(
    redis: Redis, job_type: str, run_date: str, ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS
) -> Generator[bool, None, None]:
    """Yields True if the lock was acquired (caller should proceed) or
    False if another run already holds it (caller must skip — never
    silently proceed as if it had the lock). Always releases on exit if
    it was the one holding it; never releases a lock it didn't acquire.
    """
    lock = redis.lock(_lock_key(job_type, run_date), timeout=ttl_seconds, blocking=False)
    acquired = lock.acquire()
    try:
        yield acquired
    finally:
        if acquired:
            try:
                lock.release()
            except LockError:
                # lock already expired/released (e.g. TTL elapsed under a
                # very long-running job) — nothing left to clean up.
                pass
