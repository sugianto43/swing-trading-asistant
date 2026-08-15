from dataclasses import dataclass
from datetime import date

from app.db.enums import DataQualityStatus
from app.db.models import CorporateAction, PriceBar
from app.indicators import calculations, versioning
from app.marketdata.adjustment import compute_split_adjusted_bars


@dataclass(frozen=True, slots=True)
class IndicatorSnapshotRow:
    trade_date: date
    indicator_version: str
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


def _dedupe_by_trade_date(bars: list[PriceBar]) -> list[PriceBar]:
    """Two PriceBar rows can legitimately coexist for the same
    instrument+date if ingested from different sources (Phase 2's unique
    constraint is instrument_id+trade_date+source, not just trade_date —
    e.g. a symbol re-ingested from a different provider). A rolling-window
    calculation cannot tolerate a repeated data point, so pick one bar per
    date deterministically: the most recently ingested one wins."""
    by_date: dict[date, PriceBar] = {}
    for bar in bars:
        existing = by_date.get(bar.trade_date)
        if existing is None or bar.ingested_at >= existing.ingested_at:
            by_date[bar.trade_date] = bar
    return list(by_date.values())


def compute_indicator_snapshot(
    bars: list[PriceBar], corporate_actions: list[CorporateAction]
) -> list[IndicatorSnapshotRow]:
    """Compute the canonical indicator set for an ordered bar history.

    Only VALID/SUSPECT bars are used — INVALID bars are excluded from the
    sequence entirely (treated the same as a missing session), never fed
    into a calculation (MASTER-PRD FR-003/FR-004). Prices are split-adjusted
    before any indicator math, so a split never shows up as a fake gap.
    """
    candidate_bars = [bar for bar in bars if bar.quality_status is not DataQualityStatus.INVALID]
    usable_bars = sorted(_dedupe_by_trade_date(candidate_bars), key=lambda bar: bar.trade_date)
    if not usable_bars:
        return []

    adjusted = compute_split_adjusted_bars(usable_bars, corporate_actions)

    dates = [bar.trade_date for bar in adjusted]
    highs = [bar.high for bar in adjusted]
    lows = [bar.low for bar in adjusted]
    closes = [bar.close for bar in adjusted]
    volumes = [bar.volume for bar in adjusted]

    sma_20 = calculations.sma(closes, versioning.SMA_WINDOW_20)
    sma_50 = calculations.sma(closes, versioning.SMA_WINDOW_50)
    sma_200 = calculations.sma(closes, versioning.SMA_WINDOW_200)
    ema_20 = calculations.ema(closes, versioning.EMA_WINDOW_20)
    ema_50 = calculations.ema(closes, versioning.EMA_WINDOW_50)
    rsi_14 = calculations.rsi(closes, versioning.RSI_WINDOW)
    atr_14 = calculations.atr(highs, lows, closes, versioning.ATR_WINDOW)
    macd_line, macd_signal, macd_hist = calculations.macd(
        closes, versioning.MACD_FAST, versioning.MACD_SLOW, versioning.MACD_SIGNAL
    )
    bb_upper, bb_middle, bb_lower = calculations.bollinger_bands(
        closes, versioning.BOLLINGER_WINDOW, versioning.BOLLINGER_NUM_STD
    )
    volume_sma_20 = calculations.sma([float(v) for v in volumes], versioning.VOLUME_SMA_WINDOW)
    rel_volume = calculations.relative_volume(volumes, versioning.RELATIVE_VOLUME_WINDOW)
    roll_high_20 = calculations.rolling_high(highs, versioning.ROLLING_HIGH_LOW_WINDOW)
    roll_low_20 = calculations.rolling_low(lows, versioning.ROLLING_HIGH_LOW_WINDOW)
    return_1d = calculations.returns(closes, period=1)
    volatility_20 = calculations.volatility(closes, versioning.VOLATILITY_WINDOW)

    return [
        IndicatorSnapshotRow(
            trade_date=dates[i],
            indicator_version=versioning.INDICATOR_VERSION,
            sma_20=sma_20[i],
            sma_50=sma_50[i],
            sma_200=sma_200[i],
            ema_20=ema_20[i],
            ema_50=ema_50[i],
            rsi_14=rsi_14[i],
            atr_14=atr_14[i],
            macd=macd_line[i],
            macd_signal=macd_signal[i],
            macd_histogram=macd_hist[i],
            bb_upper=bb_upper[i],
            bb_middle=bb_middle[i],
            bb_lower=bb_lower[i],
            volume_sma_20=volume_sma_20[i],
            relative_volume=rel_volume[i],
            rolling_high_20=roll_high_20[i],
            rolling_low_20=roll_low_20[i],
            return_1d=return_1d[i],
            volatility_20=volatility_20[i],
        )
        for i in range(len(dates))
    ]
