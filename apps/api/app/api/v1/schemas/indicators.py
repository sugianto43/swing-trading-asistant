from datetime import date

from pydantic import BaseModel, ConfigDict


class IndicatorSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
