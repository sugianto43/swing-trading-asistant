from dataclasses import dataclass
from datetime import date

from app.db.models import CorporateAction, IndicatorSnapshot, PriceBar
from app.marketdata.adjustment import compute_split_adjusted_bars
from app.marketdata.dedupe import dedupe_price_bars_by_trade_date


@dataclass(frozen=True, slots=True)
class ScanPoint:
    """One trading day's split-adjusted OHLCV joined with its indicator
    snapshot. Setup detectors operate on an ordered list of these — never
    on raw PriceBar/IndicatorSnapshot rows directly — so every detector
    sees prices on the same (adjusted) scale as the indicator values it
    compares them against."""

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    ema_20: float | None
    ema_50: float | None
    rsi_14: float | None
    atr_14: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    bb_upper: float | None
    bb_middle: float | None
    bb_lower: float | None
    volume_sma_20: float | None
    relative_volume: float | None
    rolling_high_20: float | None
    rolling_low_20: float | None
    return_1d: float | None
    volatility_20: float | None


def _as_float(value: float | None) -> float | None:
    # IndicatorSnapshot columns are Numeric, which SQLAlchemy loads as
    # decimal.Decimal — cast explicitly so downstream arithmetic never
    # mixes Decimal and float (which raises TypeError).
    return None if value is None else float(value)


def build_scan_points(
    bars: list[PriceBar],
    corporate_actions: list[CorporateAction],
    indicator_snapshots: list[IndicatorSnapshot],
) -> list[ScanPoint]:
    """Join split-adjusted bars with their indicator snapshots by
    trade_date. A date present in bars but missing from
    indicator_snapshots (e.g. indicators not yet computed for that date)
    is silently dropped rather than fabricating indicator values —
    callers needing indicators must have run the Phase 3 compute step
    first."""
    deduped = dedupe_price_bars_by_trade_date(bars)
    adjusted = sorted(
        compute_split_adjusted_bars(deduped, corporate_actions), key=lambda b: b.trade_date
    )
    snapshots_by_date = {snap.trade_date: snap for snap in indicator_snapshots}

    points: list[ScanPoint] = []
    for bar in adjusted:
        snapshot = snapshots_by_date.get(bar.trade_date)
        if snapshot is None:
            continue
        points.append(
            ScanPoint(
                trade_date=bar.trade_date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                sma_20=_as_float(snapshot.sma_20),
                sma_50=_as_float(snapshot.sma_50),
                sma_200=_as_float(snapshot.sma_200),
                ema_20=_as_float(snapshot.ema_20),
                ema_50=_as_float(snapshot.ema_50),
                rsi_14=_as_float(snapshot.rsi_14),
                atr_14=_as_float(snapshot.atr_14),
                macd=_as_float(snapshot.macd),
                macd_signal=_as_float(snapshot.macd_signal),
                macd_histogram=_as_float(snapshot.macd_histogram),
                bb_upper=_as_float(snapshot.bb_upper),
                bb_middle=_as_float(snapshot.bb_middle),
                bb_lower=_as_float(snapshot.bb_lower),
                volume_sma_20=_as_float(snapshot.volume_sma_20),
                relative_volume=_as_float(snapshot.relative_volume),
                rolling_high_20=_as_float(snapshot.rolling_high_20),
                rolling_low_20=_as_float(snapshot.rolling_low_20),
                return_1d=_as_float(snapshot.return_1d),
                volatility_20=_as_float(snapshot.volatility_20),
            )
        )
    return points
