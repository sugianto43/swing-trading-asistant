from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.enums import DataQualityStatus, IngestionStatus
from app.db.models import (
    CorporateAction,
    IngestionRun,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
    TradingCalendarDay,
)
from app.marketdata.provider import MarketDataProvider, RawCalendarDay
from app.marketdata.validation import (
    classify_quality,
    find_duplicate_trade_dates,
    find_missing_sessions,
    is_stale,
    validate_bar,
    validate_corporate_action,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class IngestionSummary:
    run_id: object
    status: IngestionStatus
    records_processed: int
    records_flagged: int
    notes: list[str]


class IngestionService:
    """Orchestrates provider -> validation -> idempotent persistence.

    Re-running against the same date range must not create duplicate rows
    (MASTER-PRD §20: duplicate ingestion must be handled) — persistence is
    upsert-by-natural-key, not append-only.
    """

    def __init__(self, session: Session, provider: MarketDataProvider):
        self.session = session
        self.provider = provider

    def sync_instruments(self) -> dict[str, int]:
        raw_instruments = self.provider.get_instruments()
        created = 0
        updated = 0
        for raw in raw_instruments:
            existing = self.session.scalar(
                select(Instrument).where(Instrument.symbol == raw.symbol)
            )
            if existing is None:
                instrument = Instrument(
                    symbol=raw.symbol,
                    company_name=raw.company_name,
                    exchange=raw.exchange,
                    mic=raw.mic,
                    currency=raw.currency,
                    security_type=raw.security_type,
                    sector=raw.sector,
                    subsector=raw.subsector,
                    listing_date=raw.listing_date,
                    delisting_date=raw.delisting_date,
                    status=raw.status,
                    source=raw.source,
                    source_symbol=raw.source_symbol,
                )
                self.session.add(instrument)
                self.session.flush()
                self.session.add(
                    InstrumentStatusHistory(
                        instrument_id=instrument.id,
                        status=raw.status,
                        effective_from=_utcnow(),
                        source=raw.source,
                    )
                )
                created += 1
            else:
                if existing.status != raw.status:
                    self.session.add(
                        InstrumentStatusHistory(
                            instrument_id=existing.id,
                            status=raw.status,
                            effective_from=_utcnow(),
                            source=raw.source,
                        )
                    )
                existing.company_name = raw.company_name
                existing.sector = raw.sector
                existing.subsector = raw.subsector
                existing.status = raw.status
                existing.delisting_date = raw.delisting_date
                updated += 1
        self.session.commit()
        return {"created": created, "updated": updated}

    def ingest_prices(
        self, symbol: str, start: date, end: date, as_of: date | None = None
    ) -> IngestionSummary:
        as_of = as_of or _utcnow().date()
        instrument = self.session.scalar(select(Instrument).where(Instrument.symbol == symbol))
        if instrument is None:
            raise ValueError(f"instrument not seeded: {symbol!r} (run sync_instruments first)")

        run = IngestionRun(
            provider_name=self.provider.name,
            status=IngestionStatus.RUNNING,
            records_processed=0,
            records_flagged=0,
        )
        self.session.add(run)
        # Commit the RUNNING row immediately so a failure below still leaves
        # an audit record (MASTER-PRD §20/§21) instead of being rolled back
        # along with everything else.
        self.session.commit()

        try:
            notes: list[str] = []
            raw_bars = self.provider.get_daily_bars(instrument.source_symbol, start, end)

            duplicates = find_duplicate_trade_dates(raw_bars)
            if duplicates:
                notes.append(f"provider returned duplicate trade dates: {sorted(duplicates)}")
            seen_dates: set[date] = set()
            deduped_bars = []
            for bar in raw_bars:
                if bar.trade_date in seen_dates:
                    continue
                seen_dates.add(bar.trade_date)
                deduped_bars.append(bar)
            deduped_bars.sort(key=lambda bar: bar.trade_date)

            processed = 0
            flagged = 0
            previous_valid_bar = None
            for raw_bar in deduped_bars:
                issues = validate_bar(raw_bar, as_of=as_of, previous_bar=previous_valid_bar)
                quality_status = classify_quality(issues)
                if quality_status is not DataQualityStatus.VALID:
                    flagged += 1

                existing = self.session.scalar(
                    select(PriceBar).where(
                        PriceBar.instrument_id == instrument.id,
                        PriceBar.trade_date == raw_bar.trade_date,
                        PriceBar.source == raw_bar.source,
                    )
                )
                if existing is None:
                    self.session.add(
                        PriceBar(
                            instrument_id=instrument.id,
                            trade_date=raw_bar.trade_date,
                            open=raw_bar.open,
                            high=raw_bar.high,
                            low=raw_bar.low,
                            close=raw_bar.close,
                            volume=raw_bar.volume,
                            previous_close=raw_bar.previous_close,
                            change=raw_bar.change,
                            change_percent=raw_bar.change_percent,
                            source=raw_bar.source,
                            source_symbol=raw_bar.source_symbol,
                            ingestion_run_id=run.id,
                            quality_status=quality_status,
                            quality_notes=issues or None,
                            raw_payload=raw_bar.raw_payload,
                        )
                    )
                else:
                    existing.open = raw_bar.open
                    existing.high = raw_bar.high
                    existing.low = raw_bar.low
                    existing.close = raw_bar.close
                    existing.volume = raw_bar.volume
                    existing.previous_close = raw_bar.previous_close
                    existing.change = raw_bar.change
                    existing.change_percent = raw_bar.change_percent
                    existing.ingestion_run_id = run.id
                    existing.quality_status = quality_status
                    existing.quality_notes = issues or None
                    existing.raw_payload = raw_bar.raw_payload
                processed += 1

                if quality_status is DataQualityStatus.VALID:
                    # Only a VALID bar can anchor the next bar's abnormal-volume
                    # baseline — chaining off an already-flagged bar would let a
                    # corrupted record poison the next comparison.
                    previous_valid_bar = raw_bar
                    calendar_day = self.session.scalar(
                        select(TradingCalendarDay).where(
                            TradingCalendarDay.date == raw_bar.trade_date
                        )
                    )
                    if calendar_day is None:
                        self.session.add(
                            TradingCalendarDay(
                                date=raw_bar.trade_date, is_trading_day=True, source="observed"
                            )
                        )

            # This check only detects gaps relative to trading_calendar rows
            # already in the DB — and those rows are seeded from observed
            # bars during ingestion itself (see above), including this same
            # batch. On the very first ingestion of a symbol the calendar is
            # built from exactly the bars being checked, so it cannot find a
            # gap in itself; the check only becomes meaningful once another
            # ingestion run (e.g. a different symbol) has already populated
            # calendar days this batch is missing.
            known_calendar_days = self.session.scalars(
                select(TradingCalendarDay).where(
                    TradingCalendarDay.date >= start, TradingCalendarDay.date <= end
                )
            ).all()
            missing_sessions = find_missing_sessions(
                deduped_bars,
                [
                    RawCalendarDay(
                        date=day.date, is_trading_day=day.is_trading_day, source=day.source
                    )
                    for day in known_calendar_days
                ],
            )
            if missing_sessions:
                notes.append(f"missing sessions vs known trading calendar: {missing_sessions}")

            if deduped_bars and is_stale(deduped_bars[-1].trade_date, as_of):
                notes.append(f"latest bar ({deduped_bars[-1].trade_date}) is stale as of {as_of}")

            run.finished_at = _utcnow()
            run.records_processed = processed
            run.records_flagged = flagged
            if processed == 0:
                run.status = IngestionStatus.PARTIAL
                notes.append("no bars returned by provider for the requested range")
            elif duplicates or flagged > 0:
                run.status = IngestionStatus.PARTIAL
            else:
                run.status = IngestionStatus.SUCCEEDED
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            run.status = IngestionStatus.FAILED
            run.finished_at = _utcnow()
            run.error_message = str(exc)
            self.session.add(run)
            self.session.commit()
            raise

        return IngestionSummary(
            run_id=run.id,
            status=run.status,
            records_processed=processed,
            records_flagged=flagged,
            notes=notes,
        )

    def ingest_corporate_actions(
        self, symbol: str, start: date, end: date, as_of: date | None = None
    ) -> IngestionSummary:
        as_of = as_of or _utcnow().date()
        instrument = self.session.scalar(select(Instrument).where(Instrument.symbol == symbol))
        if instrument is None:
            raise ValueError(f"instrument not seeded: {symbol!r} (run sync_instruments first)")

        run = IngestionRun(
            provider_name=self.provider.name,
            status=IngestionStatus.RUNNING,
            records_processed=0,
            records_flagged=0,
        )
        self.session.add(run)
        self.session.commit()

        try:
            notes: list[str] = []
            raw_actions = self.provider.get_corporate_actions(instrument.source_symbol, start, end)
            processed = 0
            skipped = 0
            for raw in raw_actions:
                issues = validate_corporate_action(raw, as_of=as_of)
                if issues:
                    # CorporateAction has no quality_status column to mark this
                    # record invalid in place, so — unlike price bars — it is
                    # skipped rather than silently persisted as if valid. The
                    # skip itself is recorded, never silent (MASTER-PRD FR-003).
                    skipped += 1
                    notes.append(
                        f"skipped corporate action ex_date={raw.ex_date} "
                        f"type={raw.action_type}: {issues}"
                    )
                    continue

                existing = self.session.scalar(
                    select(CorporateAction).where(
                        CorporateAction.instrument_id == instrument.id,
                        CorporateAction.action_type == raw.action_type,
                        CorporateAction.ex_date == raw.ex_date,
                        CorporateAction.source == raw.source,
                    )
                )
                if existing is None:
                    self.session.add(
                        CorporateAction(
                            instrument_id=instrument.id,
                            action_type=raw.action_type,
                            ex_date=raw.ex_date,
                            effective_date=raw.effective_date,
                            announced_at=raw.announced_at,
                            ratio=raw.ratio,
                            amount=raw.amount,
                            source=raw.source,
                            source_symbol=raw.source_symbol,
                            ingestion_run_id=run.id,
                            raw_payload=raw.raw_payload,
                        )
                    )
                else:
                    existing.effective_date = raw.effective_date
                    existing.announced_at = raw.announced_at
                    existing.ratio = raw.ratio
                    existing.amount = raw.amount
                    existing.ingestion_run_id = run.id
                    existing.raw_payload = raw.raw_payload
                processed += 1

            run.finished_at = _utcnow()
            run.records_processed = processed
            run.records_flagged = skipped
            run.status = IngestionStatus.PARTIAL if skipped else IngestionStatus.SUCCEEDED
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            run.status = IngestionStatus.FAILED
            run.finished_at = _utcnow()
            run.error_message = str(exc)
            self.session.add(run)
            self.session.commit()
            raise

        return IngestionSummary(
            run_id=run.id,
            status=run.status,
            records_processed=processed,
            records_flagged=skipped,
            notes=notes,
        )
