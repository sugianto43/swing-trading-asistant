import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.db.enums import CorporateActionType, DataQualityStatus, ListingStatus


class InstrumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    company_name: str
    exchange: str
    currency: str
    security_type: str
    sector: str | None
    subsector: str | None
    listing_date: date | None
    delisting_date: date | None
    status: ListingStatus
    source: str
    source_symbol: str


class PriceBarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    previous_close: float | None
    change: float | None
    change_percent: float | None
    source: str
    quality_status: DataQualityStatus
    quality_notes: list[str] | None


class CorporateActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action_type: CorporateActionType
    ex_date: date
    effective_date: date | None
    announced_at: datetime | None
    ratio: float | None
    amount: float | None
    source: str


class CalendarDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    is_trading_day: bool
    source: str
