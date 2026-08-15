import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import DataQualityStatus, ScanStatus
from app.db.models import (
    CorporateAction,
    IndicatorSnapshot,
    Instrument,
    PriceBar,
    ScanCandidate,
    ScanRun,
)
from app.indicators.versioning import INDICATOR_VERSION
from app.marketdata.validation import is_stale
from app.scanner.context import build_scan_points
from app.scanner.engine import run_scan
from app.scanner.scoring_config import SCORE_VERSION

DEFAULT_LOOKBACK_DAYS = 400  # enough history for SMA200 warm-up + squeeze lookback


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ScanSymbolResult:
    skipped_stale: bool
    candidates_persisted: int


class ScannerService:
    """Runs setup detection/scoring for one or many instruments as of a
    given date, gated by data freshness (MASTER-PRD §20: stale data must
    not produce a fresh signal), and persists results idempotently."""

    def __init__(self, session: Session):
        self.session = session

    def scan_symbol(
        self,
        symbol: str,
        as_of: date,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        scan_run_id: uuid.UUID | None = None,
    ) -> ScanSymbolResult:
        instrument = self.session.scalar(select(Instrument).where(Instrument.symbol == symbol))
        if instrument is None:
            raise ValueError(f"instrument not seeded: {symbol!r}")

        lookback_start = as_of - timedelta(days=lookback_days)

        bars = self.session.scalars(
            select(PriceBar).where(
                PriceBar.instrument_id == instrument.id,
                PriceBar.trade_date >= lookback_start,
                PriceBar.trade_date <= as_of,
            )
        ).all()

        latest_usable_date = max(
            (bar.trade_date for bar in bars if bar.quality_status is not DataQualityStatus.INVALID),
            default=None,
        )
        if is_stale(latest_usable_date, as_of):
            return ScanSymbolResult(skipped_stale=True, candidates_persisted=0)

        corporate_actions = self.session.scalars(
            select(CorporateAction).where(
                CorporateAction.instrument_id == instrument.id,
                CorporateAction.ex_date <= as_of,
            )
        ).all()
        indicator_snapshots = self.session.scalars(
            select(IndicatorSnapshot).where(
                IndicatorSnapshot.instrument_id == instrument.id,
                IndicatorSnapshot.indicator_version == INDICATOR_VERSION,
                IndicatorSnapshot.trade_date >= lookback_start,
                IndicatorSnapshot.trade_date <= as_of,
            )
        ).all()

        points = build_scan_points(list(bars), list(corporate_actions), list(indicator_snapshots))
        if not points:
            return ScanSymbolResult(skipped_stale=False, candidates_persisted=0)

        scan_date = points[-1].trade_date
        # Market-data ingestion and indicator computation are separate
        # steps (Phases 2 and 3) that can drift out of sync — the latest
        # PriceBar can be fresh while indicators lag behind, in which case
        # build_scan_points silently falls back to an older joined date.
        # The first freshness check above only guards against stale
        # prices; this one guards against the date actually being
        # persisted being stale, which is the one that matters.
        if is_stale(scan_date, as_of):
            return ScanSymbolResult(skipped_stale=True, candidates_persisted=0)

        candidates = run_scan(points)

        persisted = 0
        for candidate in candidates:
            existing = self.session.scalar(
                select(ScanCandidate).where(
                    ScanCandidate.instrument_id == instrument.id,
                    ScanCandidate.scan_date == scan_date,
                    ScanCandidate.setup_type == candidate.setup.setup_type,
                    ScanCandidate.indicator_version == INDICATOR_VERSION,
                    ScanCandidate.score_version == SCORE_VERSION,
                )
            )
            values = {
                "composite_score": candidate.scores.composite_score,
                "trend_score": candidate.scores.trend_score,
                "momentum_score": candidate.scores.momentum_score,
                "volume_score": candidate.scores.volume_score,
                "price_structure_score": candidate.scores.price_structure_score,
                "volatility_score": candidate.scores.volatility_score,
                "setup_quality_score": candidate.scores.setup_quality_score,
                "risk_reward_score": candidate.scores.risk_reward_score,
                "qualifying_conditions": candidate.setup.reasons,
                "invalidation_conditions": candidate.setup.invalidation_conditions,
                "scan_run_id": scan_run_id,
            }
            if existing is None:
                self.session.add(
                    ScanCandidate(
                        instrument_id=instrument.id,
                        scan_date=scan_date,
                        setup_type=candidate.setup.setup_type,
                        indicator_version=INDICATOR_VERSION,
                        score_version=SCORE_VERSION,
                        **values,
                    )
                )
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
            persisted += 1

        self.session.commit()
        return ScanSymbolResult(skipped_stale=False, candidates_persisted=persisted)

    def scan_many(self, symbols: list[str], as_of: date) -> ScanRun:
        run = ScanRun(
            scan_date=as_of,
            score_version=SCORE_VERSION,
            status=ScanStatus.RUNNING,
            symbols_scanned=0,
            symbols_skipped_stale=0,
            candidates_found=0,
        )
        self.session.add(run)
        self.session.commit()

        try:
            scanned = 0
            skipped = 0
            found = 0
            for symbol in symbols:
                result = self.scan_symbol(symbol, as_of, scan_run_id=run.id)
                scanned += 1
                if result.skipped_stale:
                    skipped += 1
                found += result.candidates_persisted

            run.finished_at = _utcnow()
            run.symbols_scanned = scanned
            run.symbols_skipped_stale = skipped
            run.candidates_found = found
            run.status = ScanStatus.PARTIAL if skipped else ScanStatus.SUCCEEDED
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            run.status = ScanStatus.FAILED
            run.finished_at = _utcnow()
            run.error_message = str(exc)
            self.session.add(run)
            self.session.commit()
            raise

        return run
