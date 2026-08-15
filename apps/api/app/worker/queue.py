"""Redis connection + RQ queue setup. Everything here is a thin,
directly-testable wrapper — `get_redis`/`get_queue` accept an optional
connection so tests can inject `fakeredis` instead of a real Redis
server (same "in-memory substitute for automated tests, real server
verified live at sign-off" discipline this codebase already uses for
Postgres/SQLite).
"""

from redis import Redis
from rq import Queue, Retry

from app.config import get_settings

DEFAULT_QUEUE_NAME = "swing-trader"
DEFAULT_RETRY = Retry(max=3, interval=[60, 300, 900])


def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def get_queue(connection: Redis | None = None) -> Queue:
    return Queue(DEFAULT_QUEUE_NAME, connection=connection or get_redis())
