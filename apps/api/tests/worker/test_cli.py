from datetime import date

import fakeredis
import pytest

import app.worker.cli as cli_module
from app.worker.cli import _parse_date, _parse_symbols, main
from app.worker.queue import get_queue


def test_parse_symbols_strips_and_uppercases() -> None:
    assert _parse_symbols(" bbca, tlkm ,,asii") == ["BBCA", "TLKM", "ASII"]


def test_parse_date() -> None:
    assert _parse_date("2024-03-01") == date(2024, 3, 1)


def test_main_requires_a_subcommand() -> None:
    with pytest.raises(SystemExit):
        main([])


def test_main_enqueue_pipeline_enqueues_a_job(monkeypatch, capsys) -> None:
    redis = fakeredis.FakeRedis()
    queue = get_queue(redis)
    monkeypatch.setattr(cli_module, "get_queue", lambda: queue)

    exit_code = main(["enqueue-pipeline", "--symbols", "bbca,tlkm", "--date", "2024-03-01"])

    assert exit_code == 0
    assert len(queue) == 1
    out = capsys.readouterr().out
    assert "enqueued pipeline job" in out


def test_main_register_scheduler_invokes_registration(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(cli_module, "get_redis", lambda: "fake-redis-connection")
    monkeypatch.setattr(
        cli_module, "register_daily_pipeline", lambda redis, symbols: calls.append((redis, symbols))
    )

    exit_code = main(["register-scheduler", "--symbols", "bbca,tlkm"])

    assert exit_code == 0
    assert calls == [("fake-redis-connection", ["BBCA", "TLKM"])]


def test_main_run_worker_starts_a_worker_in_burst_mode(monkeypatch) -> None:
    started = {}

    class FakeWorker:
        def __init__(self, queues, connection):
            started["queues"] = queues
            started["connection"] = connection

        def work(self, burst):
            started["burst"] = burst

    monkeypatch.setattr(cli_module, "get_redis", lambda: "fake-redis-connection")
    monkeypatch.setattr(cli_module, "Worker", FakeWorker)

    exit_code = main(["run-worker", "--burst"])

    assert exit_code == 0
    assert started["burst"] is True
    assert started["connection"] == "fake-redis-connection"
