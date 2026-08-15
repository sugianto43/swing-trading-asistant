import fakeredis
import pytest

from app.worker.locks import job_lock


def test_job_lock_acquires_when_free() -> None:
    redis = fakeredis.FakeRedis()
    with job_lock(redis, "INGESTION", "2024-01-01") as acquired:
        assert acquired is True


def test_job_lock_second_acquire_fails_while_held() -> None:
    """Regression target for the 'duplicate job' reliability focus: a
    second concurrent attempt to run the same stage+date must be
    rejected, never silently proceed as if it held the lock."""
    redis = fakeredis.FakeRedis()
    with job_lock(redis, "INGESTION", "2024-01-01") as first_acquired:
        assert first_acquired is True
        with job_lock(redis, "INGESTION", "2024-01-01") as second_acquired:
            assert second_acquired is False


def test_job_lock_released_after_context_exits() -> None:
    redis = fakeredis.FakeRedis()
    with job_lock(redis, "INGESTION", "2024-01-01"):
        pass
    with job_lock(redis, "INGESTION", "2024-01-01") as reacquired:
        assert reacquired is True


def test_job_lock_different_dates_do_not_contend() -> None:
    redis = fakeredis.FakeRedis()
    with job_lock(redis, "INGESTION", "2024-01-01") as first:
        assert first is True
        with job_lock(redis, "INGESTION", "2024-01-02") as second:
            assert second is True  # different date — independent lock


def test_job_lock_different_job_types_do_not_contend() -> None:
    redis = fakeredis.FakeRedis()
    with job_lock(redis, "INGESTION", "2024-01-01") as first:
        assert first is True
        with job_lock(redis, "SCANNER", "2024-01-01") as second:
            assert second is True  # different stage — independent lock


def test_job_lock_not_acquired_never_released_by_the_loser() -> None:
    """The context manager that failed to acquire must not release the
    lock the winner still holds — verified by the winner's lock still
    being effective immediately after the loser's context exits."""
    redis = fakeredis.FakeRedis()
    with job_lock(redis, "INGESTION", "2024-01-01") as first_acquired:
        assert first_acquired is True
        with job_lock(redis, "INGESTION", "2024-01-01") as second_acquired:
            assert second_acquired is False
        # loser's context has now exited — winner's lock must still hold
        with job_lock(redis, "INGESTION", "2024-01-01") as third_acquired:
            assert third_acquired is False


def test_job_lock_exception_inside_still_releases() -> None:
    redis = fakeredis.FakeRedis()
    with pytest.raises(ValueError), job_lock(redis, "INGESTION", "2024-01-01") as acquired:
        assert acquired is True
        raise ValueError("boom")

    with job_lock(redis, "INGESTION", "2024-01-01") as reacquired:
        assert reacquired is True
