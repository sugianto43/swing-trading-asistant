import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import MarketRegime


class BreadthComputeRequest(BaseModel):
    as_of: date


class BreadthSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    as_of: date
    breadth_version: str
    universe_size: int
    pct_above_sma50: float | None
    pct_above_sma200: float | None
    advancers: int
    decliners: int
    unchanged: int
    new_highs_20: int
    new_lows_20: int
    regime: MarketRegime
    regime_version: str
    created_at: datetime


class SectorPerformanceOut(BaseModel):
    sector: str
    instrument_count: int
    avg_return_pct: float


class EventOut(BaseModel):
    instrument_id: uuid.UUID
    symbol: str
    event_type: str
    announced_at: datetime
    availability_is_estimated: bool
    ex_date: date
    effective_date: date | None
    description: str
