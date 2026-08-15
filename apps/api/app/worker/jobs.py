"""Job functions: plain Python functions (no RQ/Redis dependency in the
function bodies themselves — they're just as callable directly in a
test as they are when enqueued by RQ) that wrap the existing Phase 2-9
services. Each records a JobRun audit row and, where the underlying
service operates per-symbol, tolerates one symbol's failure without
aborting the rest of the batch (TDD's "provider outage" reliability
focus — the existing marketdata CLI's un-wrapped per-symbol loop does
NOT have this property; these wrappers add it without changing the
underlying services)."""

import uuid
from datetime import UTC, date, datetime

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import (
    JobStatus,
    JobType,
    ScanStatus,
    TradePlanStatus,
)
from app.db.models import (
    IndicatorSnapshot,
    Instrument,
    JobRun,
    PriceBar,
    ScanCandidate,
    TradePlan,
)
from app.indicators.service import IndicatorService
from app.indicators.versioning import INDICATOR_VERSION
from app.intelligence.service import MarketIntelligenceService
from app.marketdata.fixture_provider import FixtureProvider
from app.marketdata.ingestion import IngestionService
from app.marketdata.provider import MarketDataProvider
from app.marketdata.validation import is_stale
from app.risk.config import RiskConfig
from app.risk.service import RiskService
from app.scanner.scoring_config import SCORE_VERSION
from app.scanner.service import ScannerService
from app.worker.alert_config import AlertConfig
from app.worker.alert_engine import (
    EventSignal,
    PricePlanSignal,
    SetupSignal,
    VolumeSignal,
    evaluate_important_event_alerts,
    evaluate_price_proximity_alerts,
    evaluate_setup_alerts,
    evaluate_stale_data_alert,
    evaluate_volume_alerts,
)
from app.worker.alert_service import AlertService


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _build_provider(name: str) -> MarketDataProvider:
    if name == "fixture":
        return FixtureProvider()
    if name == "yfinance":
        from app.marketdata.yfinance_provider import YfinanceProvider

        return YfinanceProvider()
    raise ValueError(f"unknown provider: {name!r}")


def _start_job(session: Session, job_type: JobType, run_date: date) -> JobRun:
    job = JobRun(job_type=job_type, run_date=run_date, status=JobStatus.RUNNING)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _finish_job(
    session: Session, job: JobRun, status: JobStatus, error_message: str | None = None
) -> JobRun:
    job.status = status
    job.error_message = error_message
    job.finished_at = _utcnow()
    session.commit()
    session.refresh(job)
    return job


def run_ingestion(
    session: Session,
    symbols: list[str],
    provider_name: str,
    start: date,
    end: date,
    run_date: date,
) -> JobRun:
    job = _start_job(session, JobType.INGESTION, run_date)
    provider = _build_provider(provider_name)
    service = IngestionService(session, provider)

    try:
        service.sync_instruments()
    except Exception as exc:
        return _finish_job(session, job, JobStatus.FAILED, f"sync_instruments failed: {exc}")

    failures: list[str] = []
    for symbol in symbols:
        try:
            service.ingest_prices(symbol, start, end)
            service.ingest_corporate_actions(symbol, start, end)
        except Exception as exc:
            # one symbol's provider failure must not abort the batch —
            # this is the property the raw CLI's un-wrapped loop lacks.
            failures.append(f"{symbol}: {exc}")

    if failures and len(failures) == len(symbols):
        return _finish_job(session, job, JobStatus.FAILED, "; ".join(failures))
    if failures:
        return _finish_job(session, job, JobStatus.PARTIAL, "; ".join(failures))
    return _finish_job(session, job, JobStatus.SUCCEEDED)


def run_indicators(
    session: Session, symbols: list[str], start: date, end: date, run_date: date
) -> JobRun:
    job = _start_job(session, JobType.INDICATORS, run_date)
    service = IndicatorService(session)

    failures: list[str] = []
    for symbol in symbols:
        try:
            service.compute_and_persist(symbol, persist_from=start, persist_to=end)
        except Exception as exc:
            failures.append(f"{symbol}: {exc}")

    if failures and len(failures) == len(symbols):
        return _finish_job(session, job, JobStatus.FAILED, "; ".join(failures))
    if failures:
        return _finish_job(session, job, JobStatus.PARTIAL, "; ".join(failures))
    return _finish_job(session, job, JobStatus.SUCCEEDED)


def run_scanner(session: Session, symbols: list[str], as_of: date, run_date: date) -> JobRun:
    job = _start_job(session, JobType.SCANNER, run_date)
    service = ScannerService(session)
    try:
        scan_run = service.scan_many(symbols, as_of)
    except Exception as exc:
        return _finish_job(session, job, JobStatus.FAILED, str(exc))

    status = {
        ScanStatus.SUCCEEDED: JobStatus.SUCCEEDED,
        ScanStatus.PARTIAL: JobStatus.PARTIAL,
        ScanStatus.FAILED: JobStatus.FAILED,
    }.get(scan_run.status, JobStatus.FAILED)
    return _finish_job(session, job, status, scan_run.error_message)


def run_risk_plans(
    session: Session,
    as_of: date,
    run_date: date,
    capital: float,
    config: RiskConfig | None = None,
) -> JobRun:
    """Builds a trade plan for every qualifying scan candidate found
    today — this orchestration (batch-over-today's-candidates) doesn't
    exist in Phase 6's CLI, which only ever builds one symbol/setup at a
    time; the scheduler needs to drive it across the whole day's
    candidates."""
    job = _start_job(session, JobType.RISK_PLANS, run_date)
    try:
        candidates = session.scalars(
            select(ScanCandidate).where(
                ScanCandidate.scan_date == as_of, ScanCandidate.score_version == SCORE_VERSION
            )
        ).all()
        instrument_by_id = {
            i.id: i
            for i in session.scalars(
                select(Instrument).where(Instrument.id.in_({c.instrument_id for c in candidates}))
            ).all()
        }

        service = RiskService(session)
        failures: list[str] = []
        for candidate in candidates:
            instrument = instrument_by_id.get(candidate.instrument_id)
            if instrument is None:
                continue
            try:
                service.build_plan(
                    symbol=instrument.symbol,
                    setup_type=candidate.setup_type,
                    plan_date=as_of,
                    capital=capital,
                    config=config,
                )
            except Exception as exc:
                failures.append(f"{instrument.symbol}: {exc}")
    except Exception as exc:
        return _finish_job(session, job, JobStatus.FAILED, str(exc))

    if failures and candidates and len(failures) == len(candidates):
        return _finish_job(session, job, JobStatus.FAILED, "; ".join(failures))
    if failures:
        return _finish_job(session, job, JobStatus.PARTIAL, "; ".join(failures))
    return _finish_job(session, job, JobStatus.SUCCEEDED)


def run_breadth(session: Session, as_of: date, run_date: date) -> JobRun:
    job = _start_job(session, JobType.BREADTH, run_date)
    try:
        MarketIntelligenceService(session).compute_breadth_snapshot(as_of)
    except Exception as exc:
        return _finish_job(session, job, JobStatus.FAILED, str(exc))
    return _finish_job(session, job, JobStatus.SUCCEEDED)


def run_alerts(
    session: Session,
    as_of: date,
    run_date: date,
    redis: Redis | None = None,
    config: AlertConfig | None = None,
) -> JobRun:
    """Evaluates every mechanically-derivable alert type (see
    alert_engine.py's module docstring for what's deliberately excluded)
    over today's scan candidates, valid trade plans, and newly-announced
    events, then persists deduplicated results."""
    job = _start_job(session, JobType.ALERTS, run_date)
    config = config or AlertConfig()

    try:
        candidates = session.scalars(
            select(ScanCandidate).where(
                ScanCandidate.scan_date == as_of, ScanCandidate.score_version == SCORE_VERSION
            )
        ).all()
        plans = session.scalars(
            select(TradePlan).where(
                TradePlan.plan_date == as_of, TradePlan.status == TradePlanStatus.VALID
            )
        ).all()

        watchlist_ids: set[uuid.UUID] = {c.instrument_id for c in candidates} | {
            p.instrument_id for p in plans
        }
        instruments = session.scalars(
            select(Instrument).where(Instrument.id.in_(watchlist_ids))
        ).all()
        instrument_by_id = {i.id: i for i in instruments}

        latest_bar_by_instrument: dict[uuid.UUID, PriceBar] = {}
        for instrument_id in watchlist_ids:
            bar = session.scalar(
                select(PriceBar)
                .where(PriceBar.instrument_id == instrument_id, PriceBar.trade_date <= as_of)
                .order_by(PriceBar.trade_date.desc())
                .limit(1)
            )
            if bar is not None:
                latest_bar_by_instrument[instrument_id] = bar

        all_candidates = []

        setup_signals = [
            SetupSignal(
                instrument_id=c.instrument_id,
                symbol=instrument_by_id[c.instrument_id].symbol,
                setup_type=c.setup_type.value,
                composite_score=float(c.composite_score),
            )
            for c in candidates
            if c.instrument_id in instrument_by_id
        ]
        all_candidates += evaluate_setup_alerts(setup_signals)

        price_signals = []
        for plan in plans:
            instrument = instrument_by_id.get(plan.instrument_id)
            bar = latest_bar_by_instrument.get(plan.instrument_id)
            if instrument is None or bar is None:
                continue
            target_prices = plan.target_prices or []
            price_signals.append(
                PricePlanSignal(
                    instrument_id=plan.instrument_id,
                    symbol=instrument.symbol,
                    current_price=float(bar.close),
                    entry_price=float(plan.entry_price) if plan.entry_price is not None else None,
                    stop_price=float(plan.stop_price) if plan.stop_price is not None else None,
                    target_price=float(target_prices[-1]) if target_prices else None,
                )
            )
        all_candidates += evaluate_price_proximity_alerts(price_signals, config)

        indicator_by_instrument: dict[uuid.UUID, IndicatorSnapshot] = {
            snap.instrument_id: snap
            for snap in session.scalars(
                select(IndicatorSnapshot).where(
                    IndicatorSnapshot.instrument_id.in_(watchlist_ids),
                    IndicatorSnapshot.trade_date == as_of,
                    IndicatorSnapshot.indicator_version == INDICATOR_VERSION,
                )
            ).all()
        }
        volume_signals = [
            VolumeSignal(
                instrument_id=c.instrument_id,
                symbol=instrument_by_id[c.instrument_id].symbol,
                relative_volume=(
                    float(snap.relative_volume)
                    if (snap := indicator_by_instrument.get(c.instrument_id)) is not None
                    and snap.relative_volume is not None
                    else None
                ),
            )
            for c in candidates
            if c.instrument_id in instrument_by_id
        ]
        all_candidates += evaluate_volume_alerts(volume_signals, config)

        for instrument_id in watchlist_ids:
            instrument = instrument_by_id.get(instrument_id)
            bar = latest_bar_by_instrument.get(instrument_id)
            if instrument is None:
                continue
            if bar is None or is_stale(bar.trade_date, as_of):
                all_candidates.append(evaluate_stale_data_alert(instrument_id, instrument.symbol))

        events = MarketIntelligenceService(session).get_events(symbol=None, as_of=as_of)
        event_signals = []
        for e in events:
            if e.announced_at.date() != as_of:
                continue
            event_instrument = instrument_by_id.get(e.instrument_id)
            event_symbol = event_instrument.symbol if event_instrument else str(e.instrument_id)
            event_signals.append(
                EventSignal(
                    instrument_id=e.instrument_id,
                    symbol=event_symbol,
                    event_type=e.event_type,
                    description=e.description,
                )
            )
        all_candidates += evaluate_important_event_alerts(event_signals)

        AlertService(session, redis).persist_alerts(all_candidates, as_of)
    except Exception as exc:
        return _finish_job(session, job, JobStatus.FAILED, str(exc))

    return _finish_job(session, job, JobStatus.SUCCEEDED)
