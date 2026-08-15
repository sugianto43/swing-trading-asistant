import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtesting.universe import is_active_as_of
from app.db.models import (
    BreadthSnapshot,
    CorporateAction,
    IndicatorSnapshot,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
)
from app.indicators.versioning import INDICATOR_VERSION
from app.intelligence.breadth_engine import BreadthInput, compute_breadth
from app.intelligence.config import BREADTH_VERSION, RegimeConfig
from app.intelligence.event_mapper import Event, corporate_action_to_event
from app.intelligence.regime_engine import classify_regime

PRIOR_CLOSE_LOOKBACK_DAYS = 10  # enough to find the previous trading day across a weekend/holiday


@dataclass(frozen=True, slots=True)
class SectorPerformance:
    sector: str
    instrument_count: int
    avg_return_pct: float


class MarketIntelligenceService:
    def __init__(self, session: Session):
        self.session = session

    def _active_instruments(self, as_of: date) -> list[Instrument]:
        instruments = self.session.scalars(select(Instrument)).all()
        history_by_instrument: dict[uuid.UUID, list[InstrumentStatusHistory]] = defaultdict(list)
        for h in self.session.scalars(select(InstrumentStatusHistory)).all():
            history_by_instrument[h.instrument_id].append(h)
        return [
            instrument
            for instrument in instruments
            if is_active_as_of(instrument, history_by_instrument.get(instrument.id, []), as_of)
        ]

    def compute_breadth_snapshot(
        self, as_of: date, config: RegimeConfig | None = None
    ) -> BreadthSnapshot:
        config = config or RegimeConfig()
        active_instruments = self._active_instruments(as_of)
        active_ids = [i.id for i in active_instruments]

        indicator_by_instrument: dict[uuid.UUID, IndicatorSnapshot] = {
            snap.instrument_id: snap
            for snap in self.session.scalars(
                select(IndicatorSnapshot).where(
                    IndicatorSnapshot.instrument_id.in_(active_ids),
                    IndicatorSnapshot.trade_date == as_of,
                    IndicatorSnapshot.indicator_version == INDICATOR_VERSION,
                )
            ).all()
        }

        lookback_start = as_of - timedelta(days=PRIOR_CLOSE_LOOKBACK_DAYS)
        bars_by_instrument: dict[uuid.UUID, list[PriceBar]] = defaultdict(list)
        for bar in self.session.scalars(
            select(PriceBar).where(
                PriceBar.instrument_id.in_(active_ids),
                PriceBar.trade_date >= lookback_start,
                PriceBar.trade_date <= as_of,
            )
        ).all():
            bars_by_instrument[bar.instrument_id].append(bar)

        points: list[BreadthInput] = []
        for instrument_id in active_ids:
            snapshot = indicator_by_instrument.get(instrument_id)
            if snapshot is None:
                continue  # no indicator data for this exact date — excluded, not fabricated
            bars = sorted(bars_by_instrument.get(instrument_id, []), key=lambda b: b.trade_date)
            today_bar = next((b for b in bars if b.trade_date == as_of), None)
            if today_bar is None:
                continue
            prior_bars = [b for b in bars if b.trade_date < as_of]
            prior_close = float(prior_bars[-1].close) if prior_bars else None

            points.append(
                BreadthInput(
                    instrument_id=instrument_id,
                    close=float(today_bar.close),
                    prior_close=prior_close,
                    sma_50=float(snapshot.sma_50) if snapshot.sma_50 is not None else None,
                    sma_200=float(snapshot.sma_200) if snapshot.sma_200 is not None else None,
                    rolling_high_20=float(snapshot.rolling_high_20)
                    if snapshot.rolling_high_20 is not None
                    else None,
                    rolling_low_20=float(snapshot.rolling_low_20)
                    if snapshot.rolling_low_20 is not None
                    else None,
                )
            )

        breadth = compute_breadth(points)
        regime = classify_regime(breadth, config)

        existing = self.session.scalar(
            select(BreadthSnapshot).where(
                BreadthSnapshot.as_of == as_of,
                BreadthSnapshot.breadth_version == BREADTH_VERSION,
            )
        )
        values = {
            "universe_size": breadth.universe_size,
            "pct_above_sma50": breadth.pct_above_sma50,
            "pct_above_sma200": breadth.pct_above_sma200,
            "advancers": breadth.advancers,
            "decliners": breadth.decliners,
            "unchanged": breadth.unchanged,
            "new_highs_20": breadth.new_highs_20,
            "new_lows_20": breadth.new_lows_20,
            "regime": regime.regime,
            "regime_version": regime.regime_version,
        }
        if existing is None:
            snapshot_row = BreadthSnapshot(as_of=as_of, breadth_version=BREADTH_VERSION, **values)
            self.session.add(snapshot_row)
        else:
            for field, value in values.items():
                setattr(existing, field, value)
            snapshot_row = existing
        self.session.commit()
        self.session.refresh(snapshot_row)
        return snapshot_row

    def get_breadth_snapshot(self, as_of: date | None = None) -> BreadthSnapshot | None:
        # pinned to the current BREADTH_VERSION, matching the write path
        # (compute_breadth_snapshot's upsert lookup) — without this, once
        # a second breadth_version ever exists for the same as_of, which
        # row comes back would be arbitrary DB row order, not "the
        # current configuration's result" (MASTER-PRD §21 traceability).
        query = select(BreadthSnapshot).where(BreadthSnapshot.breadth_version == BREADTH_VERSION)
        if as_of is not None:
            query = query.where(BreadthSnapshot.as_of == as_of)
        return self.session.scalar(
            query.order_by(BreadthSnapshot.as_of.desc(), BreadthSnapshot.created_at.desc()).limit(1)
        )

    def sector_performance(self, as_of: date, lookback_days: int) -> list[SectorPerformance]:
        active_instruments = [i for i in self._active_instruments(as_of) if i.sector]
        active_ids = [i.id for i in active_instruments]
        sector_by_id: dict[uuid.UUID, str] = {
            i.id: i.sector for i in active_instruments if i.sector is not None
        }

        lookback_start = as_of - timedelta(days=lookback_days + PRIOR_CLOSE_LOOKBACK_DAYS)
        bars_by_instrument: dict[uuid.UUID, list[PriceBar]] = defaultdict(list)
        for bar in self.session.scalars(
            select(PriceBar).where(
                PriceBar.instrument_id.in_(active_ids),
                PriceBar.trade_date >= lookback_start,
                PriceBar.trade_date <= as_of,
            )
        ).all():
            bars_by_instrument[bar.instrument_id].append(bar)

        returns_by_sector: dict[str, list[float]] = defaultdict(list)
        window_start = as_of - timedelta(days=lookback_days)
        for instrument_id, bars in bars_by_instrument.items():
            bars_sorted = sorted(bars, key=lambda b: b.trade_date)
            end_bar = next((b for b in reversed(bars_sorted) if b.trade_date <= as_of), None)
            # latest bar at or before window_start — the one closest to the
            # intended "N days ago" reference point, not the oldest bar in
            # the fetch buffer (a prior bug: iterating bars_sorted forward
            # here picked whatever the earliest bar in the whole buffer
            # was, silently using a stale price up to
            # PRIOR_CLOSE_LOOKBACK_DAYS too early).
            start_bar = next(
                (b for b in reversed(bars_sorted) if b.trade_date <= window_start), None
            )
            if end_bar is None or start_bar is None or float(start_bar.close) <= 0:
                continue
            return_pct = (
                (float(end_bar.close) - float(start_bar.close)) / float(start_bar.close) * 100
            )
            returns_by_sector[sector_by_id[instrument_id]].append(return_pct)

        return [
            SectorPerformance(
                sector=sector,
                instrument_count=len(returns),
                avg_return_pct=sum(returns) / len(returns),
            )
            for sector, returns in returns_by_sector.items()
        ]

    def get_events(self, symbol: str | None, as_of: date | None) -> list[Event]:
        query = select(CorporateAction)
        if symbol is not None:
            instrument = self.session.scalar(
                select(Instrument).where(Instrument.symbol == symbol.upper())
            )
            if instrument is None:
                return []
            query = query.where(CorporateAction.instrument_id == instrument.id)

        actions = self.session.scalars(query).all()
        events = [corporate_action_to_event(ca) for ca in actions]
        if as_of is not None:
            # Critical Rule (TDD): historical analysis uses information
            # only from its public-availability timestamp — never
            # ex_date/effective_date, which can be known/scheduled ahead
            # of when the action actually became public knowledge.
            events = [e for e in events if e.announced_at.date() <= as_of]
        return sorted(events, key=lambda e: e.announced_at, reverse=True)
