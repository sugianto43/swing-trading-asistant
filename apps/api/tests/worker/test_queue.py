import fakeredis

from app.worker.queue import DEFAULT_QUEUE_NAME, get_queue


def test_get_queue_uses_default_name() -> None:
    redis = fakeredis.FakeRedis()
    queue = get_queue(redis)
    assert queue.name == DEFAULT_QUEUE_NAME


def test_get_queue_starts_empty() -> None:
    redis = fakeredis.FakeRedis()
    queue = get_queue(redis)
    assert len(queue) == 0


def test_get_queue_enqueue_increases_depth() -> None:
    redis = fakeredis.FakeRedis()
    queue = get_queue(redis)
    queue.enqueue(len, [1, 2, 3])
    assert len(queue) == 1
