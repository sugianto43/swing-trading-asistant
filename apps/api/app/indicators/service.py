from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CorporateAction, IndicatorSnapshot, Instrument, PriceBar
from app.indicators import versioning
from app.indicators.engine import compute_indicator_snapshot


@dataclass(frozen=True, slots=True)
class IndicatorComputeSummary:
    computed: int
    persisted: int


class IndicatorService:
    """Computes and idempotently persists indicator snapshots.

    Re-running for the same date range must not create duplicate rows —
    persistence is upsert-by-natural-key (instrument_id, trade_date,
    indicator_version), same pattern as market-data ingestion.
    """

    def __init__(self, session: Session):
        self.session = session

    def compute_and_persist(
        self, symbol: str, persist_from: date, persist_to: date
    ) -> IndicatorComputeSummary:
        instrument = self.session.scalar(select(Instrument).where(Instrument.symbol == symbol))
        if instrument is None:
            raise ValueError(f"instrument not seeded: {symbol!r}")

        # Fetch full history up to persist_to (no lower bound) so rolling
        # windows/warm-up are computed correctly even when persist_from is
        # deep into an instrument's history.
        bars = self.session.scalars(
            select(PriceBar)
            .where(PriceBar.instrument_id == instrument.id, PriceBar.trade_date <= persist_to)
            .order_by(PriceBar.trade_date)
        ).all()
        # Bounded by persist_to for the same reason as the bars query above:
        # a split ingested after persist_to must not retroactively adjust a
        # historical snapshot computed "as of" an earlier date (MASTER-PRD
        # §8 — only information available at or before T).
        corporate_actions = self.session.scalars(
            select(CorporateAction).where(
                CorporateAction.instrument_id == instrument.id,
                CorporateAction.ex_date <= persist_to,
            )
        ).all()

        rows = compute_indicator_snapshot(list(bars), list(corporate_actions))
        rows_in_range = [row for row in rows if persist_from <= row.trade_date <= persist_to]

        # Batch pre-fetch instead of one SELECT per row — a multi-year
        # backfill can mean thousands of rows, and this collapses that to a
        # single query.
        existing_by_date = {
            snapshot.trade_date: snapshot
            for snapshot in self.session.scalars(
                select(IndicatorSnapshot).where(
                    IndicatorSnapshot.instrument_id == instrument.id,
                    IndicatorSnapshot.indicator_version == versioning.INDICATOR_VERSION,
                    IndicatorSnapshot.trade_date >= persist_from,
                    IndicatorSnapshot.trade_date <= persist_to,
                )
            )
        }

        persisted = 0
        for row in rows_in_range:
            existing = existing_by_date.get(row.trade_date)
            values = {
                "sma_20": row.sma_20,
                "sma_50": row.sma_50,
                "sma_200": row.sma_200,
                "ema_20": row.ema_20,
                "ema_50": row.ema_50,
                "rsi_14": row.rsi_14,
                "atr_14": row.atr_14,
                "macd": row.macd,
                "macd_signal": row.macd_signal,
                "macd_histogram": row.macd_histogram,
                "bb_upper": row.bb_upper,
                "bb_middle": row.bb_middle,
                "bb_lower": row.bb_lower,
                "volume_sma_20": row.volume_sma_20,
                "relative_volume": row.relative_volume,
                "rolling_high_20": row.rolling_high_20,
                "rolling_low_20": row.rolling_low_20,
                "return_1d": row.return_1d,
                "volatility_20": row.volatility_20,
            }
            if existing is None:
                self.session.add(
                    IndicatorSnapshot(
                        instrument_id=instrument.id,
                        trade_date=row.trade_date,
                        indicator_version=row.indicator_version,
                        **values,
                    )
                )
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
            persisted += 1

        self.session.commit()
        return IndicatorComputeSummary(computed=len(rows), persisted=persisted)
