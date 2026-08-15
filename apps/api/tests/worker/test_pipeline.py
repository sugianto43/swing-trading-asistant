from datetime import date, timedelta

import fakeredis

import app.worker.pipeline as pipeline_module
from app.db.enums import JobType
from app.worker.locks import job_lock
from app.worker.pipeline import DEFAULT_INGESTION_LOOKBACK_DAYS, enqueue_pipeline

AS_OF = date(2024, 3, 1)


def _patch_all_stages(monkeypatch, calls: list) -> None:
    monkeypatch.setattr(
        pipeline_module,
        "run_ingestion",
        lambda s, symbols, provider, start, end, run_date: calls.append(
            (JobType.INGESTION, symbols, start, end)
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "run_indicators",
        lambda s, symbols, start, end, run_date: calls.append(
            (JobType.INDICATORS, symbols, start, end)
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "run_scanner",
        lambda s, symbols, as_of, run_date: calls.append((JobType.SCANNER, symbols, as_of)),
    )
    monkeypatch.setattr(
        pipeline_module,
        "run_risk_plans",
        lambda s, as_of, run_date, capital: calls.append((JobType.RISK_PLANS, as_of, capital)),
    )
    monkeypatch.setattr(
        pipeline_module,
        "run_breadth",
        lambda s, as_of, run_date: calls.append((JobType.BREADTH, as_of)),
    )
    monkeypatch.setattr(
        pipeline_module,
        "run_alerts",
        lambda s, as_of, run_date, redis=None: calls.append((JobType.ALERTS, as_of)),
    )


def test_enqueue_pipeline_runs_all_stages_in_order(monkeypatch) -> None:
    redis = fakeredis.FakeRedis()
    calls: list = []
    _patch_all_stages(monkeypatch, calls)

    results = enqueue_pipeline(["BBCA"], as_of=AS_OF, redis=redis)

    assert len(results) == 6
    stage_order = [c[0] for c in calls]
    assert stage_order == [
        JobType.INGESTION,
        JobType.INDICATORS,
        JobType.SCANNER,
        JobType.RISK_PLANS,
        JobType.BREADTH,
        JobType.ALERTS,
    ]


def test_enqueue_pipeline_ingestion_uses_lookback_window(monkeypatch) -> None:
    redis = fakeredis.FakeRedis()
    calls: list = []
    _patch_all_stages(monkeypatch, calls)

    enqueue_pipeline(["BBCA"], as_of=AS_OF, redis=redis)

    ingestion_call = next(c for c in calls if c[0] == JobType.INGESTION)
    assert ingestion_call[2] == AS_OF - timedelta(days=DEFAULT_INGESTION_LOOKBACK_DAYS)
    assert ingestion_call[3] == AS_OF


def test_enqueue_pipeline_skips_stage_already_locked(monkeypatch) -> None:
    """Regression target for the 'duplicate job' reliability focus: an
    overlapping enqueue for a stage already running must be a safe no-op
    (None in results), not a double-run."""
    redis = fakeredis.FakeRedis()
    calls: list = []
    _patch_all_stages(monkeypatch, calls)

    with job_lock(redis, JobType.INGESTION.value, AS_OF.isoformat()) as acquired:
        assert acquired is True
        results = enqueue_pipeline(["BBCA"], as_of=AS_OF, redis=redis)

    assert results[0] is None  # ingestion stage was skipped
    stage_order = [c[0] for c in calls]
    assert JobType.INGESTION not in stage_order
    assert stage_order == [
        JobType.INDICATORS,
        JobType.SCANNER,
        JobType.RISK_PLANS,
        JobType.BREADTH,
        JobType.ALERTS,
    ]


def test_enqueue_pipeline_defaults_as_of_to_today(monkeypatch) -> None:
    redis = fakeredis.FakeRedis()
    calls: list = []
    _patch_all_stages(monkeypatch, calls)

    enqueue_pipeline(["BBCA"], redis=redis)

    scanner_call = next(c for c in calls if c[0] == JobType.SCANNER)
    assert scanner_call[2] == date.today()
