from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from app.db.enums import CorporateActionType, ListingStatus


class ProviderError(Exception):
    """Raised when a provider fails to fetch data.

    Provider-specific exceptions (HTTP errors, library-specific errors,
    etc.) must be caught and re-raised as this type so vendor-specific
    failure modes never leak into domain/ingestion logic.
    """


@dataclass(frozen=True, slots=True)
class RawInstrument:
    symbol: str
    source_symbol: str
    company_name: str
    source: str
    exchange: str = "IDX"
    mic: str | None = None
    currency: str = "IDR"
    security_type: str = "EQUITY"
    sector: str | None = None
    subsector: str | None = None
    listing_date: date | None = None
    delisting_date: date | None = None
    status: ListingStatus = ListingStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class RawBar:
    source_symbol: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str
    previous_close: float | None = None
    change: float | None = None
    change_percent: float | None = None
    raw_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class RawCorporateAction:
    source_symbol: str
    action_type: CorporateActionType
    ex_date: date
    source: str
    effective_date: date | None = None
    announced_at: datetime | None = None
    ratio: float | None = None
    amount: float | None = None
    raw_payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class RawCalendarDay:
    date: date
    is_trading_day: bool
    source: str


class MarketDataProvider(Protocol):
    """Provider-agnostic contract. Vendor-specific schemas must never leak
    past this boundary (docs/data/DATA-VENDOR-REQUIREMENTS.md §1, §22)."""

    name: str

    def get_instruments(self) -> list[RawInstrument]: ...

    def get_daily_bars(self, source_symbol: str, start: date, end: date) -> list[RawBar]: ...

    def get_corporate_actions(
        self, source_symbol: str, start: date, end: date
    ) -> list[RawCorporateAction]: ...

    def get_calendar(self, start: date, end: date) -> list[RawCalendarDay]: ...

    def get_latest_quote(self, source_symbol: str) -> RawBar | None: ...
