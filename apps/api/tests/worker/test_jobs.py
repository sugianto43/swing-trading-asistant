from datetime import date, timedelta

from sqlalchemy import select

from app.db.enums import JobStatus, SetupType
from app.db.models import Alert, JobRun, TradePlan
from app.marketdata.fixture_provider import FixtureProvider
from app.marketdata.provider import RawBar
from app.worker.jobs import (
    run_alerts,
    run_breadth,
    run_indicators,
    run_ingestion,
    run_risk_plans,
    run_scanner,
)
from tests.worker.conftest import seed_instrument, seed_price_and_indicator, seed_scan_candidate

AS_OF = date(2024, 3, 1)
START = AS_OF - timedelta(days=10)


def _bar(day_offset: int, source_symbol: str = "BBCA.JK") -> RawBar:
    return RawBar(
        source_symbol=source_symbol,
        trade_date=START + timedelta(days=day_offset),
        open=1000.0,
        high=1010.0,
        low=990.0,
        close=1000.0,
        volume=1_000_000,
        source="fixture",
    )


def test_run_ingestion_happy_path(db_session) -> None:
    bars = {"BBCA.JK": [_bar(i) for i in range(5)]}
    provider = FixtureProvider(bars=bars)

    job = run_ingestion(db_session, ["BBCA"], "fixture", START, AS_OF, AS_OF)

    assert job.status == JobStatus.SUCCEEDED
    persisted = db_session.scalar(select(JobRun).where(JobRun.id == job.id))
    assert persisted is not None
    assert persisted.finished_at is not None
    del provider  # provider is rebuilt internally by run_ingestion via _build_provider("fixture")


def test_run_ingestion_one_symbol_failure_yields_partial(db_session, monkeypatch) -> None:
    """Regression target for the 'provider outage' reliability focus: one
    symbol's ingestion failure must not abort the whole batch."""
    import app.worker.jobs as jobs_module
    from app.marketdata.ingestion import IngestionService

    original_ingest_prices = IngestionService.ingest_prices

    def flaky_ingest_prices(self, symbol, start, end, as_of=None):
        if symbol == "BAD":
            raise RuntimeError("provider outage")
        return original_ingest_prices(self, symbol, start, end, as_of)

    monkeypatch.setattr(IngestionService, "ingest_prices", flaky_ingest_prices)

    def build_provider_with_bars(name: str):
        return FixtureProvider(
            instruments=[
                *FixtureProvider().get_instruments(),
            ],
            bars={"BBCA.JK": [_bar(i) for i in range(5)]},
        )

    monkeypatch.setattr(jobs_module, "_build_provider", build_provider_with_bars)

    job = run_ingestion(db_session, ["BBCA", "BAD"], "fixture", START, AS_OF, AS_OF)

    assert job.status == JobStatus.PARTIAL
    assert job.error_message is not None and "BAD" in job.error_message


def test_run_ingestion_all_symbols_fail_yields_failed(db_session, monkeypatch) -> None:
    import app.worker.jobs as jobs_module

    def build_broken_provider(name: str):
        class BrokenProvider:
            def get_instruments(self):
                return FixtureProvider().get_instruments()

            def get_daily_bars(self, source_symbol, start, end):
                raise RuntimeError("provider outage")

            def get_corporate_actions(self, source_symbol, start, end):
                raise RuntimeError("provider outage")

            def get_latest_quote(self, source_symbol):
                return None

            name = "broken"

        return BrokenProvider()

    monkeypatch.setattr(jobs_module, "_build_provider", build_broken_provider)

    job = run_ingestion(db_session, ["BBCA"], "fixture", START, AS_OF, AS_OF)

    assert job.status == JobStatus.FAILED


def test_run_indicators_happy_path(db_session) -> None:
    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF)

    job = run_indicators(db_session, ["BBCA"], START, AS_OF, AS_OF)

    assert job.status == JobStatus.SUCCEEDED


def test_run_indicators_unseeded_symbol_yields_failed(db_session) -> None:
    job = run_indicators(db_session, ["NOPE"], START, AS_OF, AS_OF)

    assert job.status == JobStatus.FAILED
    assert job.error_message is not None and "NOPE" in job.error_message


def test_run_indicators_partial_when_one_symbol_unseeded(db_session) -> None:
    instrument = seed_instrument(db_session, symbol="BBCA")
    seed_price_and_indicator(db_session, instrument, AS_OF)

    job = run_indicators(db_session, ["BBCA", "NOPE"], START, AS_OF, AS_OF)

    assert job.status == JobStatus.PARTIAL


def test_run_scanner_maps_scan_status_to_job_status(db_session) -> None:
    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF, days=1)

    job = run_scanner(db_session, ["BBCA"], AS_OF, AS_OF)

    assert job.status in {JobStatus.SUCCEEDED, JobStatus.PARTIAL, JobStatus.FAILED}
    assert job.finished_at is not None


def test_run_risk_plans_builds_plan_for_qualifying_candidate(db_session) -> None:
    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF)
    seed_scan_candidate(db_session, instrument, AS_OF)

    job = run_risk_plans(db_session, AS_OF, AS_OF, capital=100_000_000.0)

    assert job.status == JobStatus.SUCCEEDED
    plan = db_session.scalar(select(TradePlan).where(TradePlan.instrument_id == instrument.id))
    assert plan is not None


def test_run_risk_plans_no_candidates_still_succeeds(db_session) -> None:
    job = run_risk_plans(db_session, AS_OF, AS_OF, capital=100_000_000.0)

    assert job.status == JobStatus.SUCCEEDED


def test_run_breadth_happy_path(db_session) -> None:
    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF)

    job = run_breadth(db_session, AS_OF, AS_OF)

    assert job.status == JobStatus.SUCCEEDED


def test_run_alerts_persists_setup_alert_for_scan_candidate(db_session) -> None:
    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF)
    seed_scan_candidate(db_session, instrument, AS_OF, setup_type=SetupType.MA_RECLAIM)

    job = run_alerts(db_session, AS_OF, AS_OF)

    assert job.status == JobStatus.SUCCEEDED
    alerts = db_session.scalars(select(Alert)).all()
    assert len(alerts) >= 1


def test_run_alerts_is_deduplicated_on_rerun(db_session) -> None:
    """Regression target for the 'duplicate alert' reliability focus."""
    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF)
    seed_scan_candidate(db_session, instrument, AS_OF, setup_type=SetupType.MA_RECLAIM)

    run_alerts(db_session, AS_OF, AS_OF)
    first_count = len(db_session.scalars(select(Alert)).all())

    run_alerts(db_session, AS_OF, AS_OF)
    second_count = len(db_session.scalars(select(Alert)).all())

    assert first_count == second_count


def test_run_alerts_emits_stale_data_alert(db_session) -> None:
    instrument = seed_instrument(db_session)
    stale_date = AS_OF - timedelta(days=30)
    seed_price_and_indicator(db_session, instrument, stale_date)
    seed_scan_candidate(db_session, instrument, AS_OF, setup_type=SetupType.MA_RECLAIM)

    run_alerts(db_session, AS_OF, AS_OF)

    alerts = db_session.scalars(select(Alert)).all()
    from app.db.enums import AlertType

    assert any(a.alert_type == AlertType.STALE_DATA for a in alerts)


def test_run_alerts_job_run_never_left_running_on_exception(db_session, monkeypatch) -> None:
    import app.worker.jobs as jobs_module

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(jobs_module, "evaluate_setup_alerts", boom)

    instrument = seed_instrument(db_session)
    seed_price_and_indicator(db_session, instrument, AS_OF)
    seed_scan_candidate(db_session, instrument, AS_OF)

    job = run_alerts(db_session, AS_OF, AS_OF)

    assert job.status == JobStatus.FAILED
    assert job.finished_at is not None
