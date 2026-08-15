from datetime import date

from app.marketdata.provider import (
    RawBar,
    RawCalendarDay,
    RawCorporateAction,
    RawInstrument,
)
from app.marketdata.seed import load_seed_instruments

FIXTURE_SOURCE = "fixture"


class FixtureProvider:
    """Deterministic, network-free provider (docs/data/DATA-VENDOR-REQUIREMENTS.md §17:
    a mock provider is mandatory and tests must not depend on internet access).

    Data is injected at construction time so tests can exercise adversarial
    cases (duplicates, invalid OHLC, missing sessions, stale data) without
    encoding them into shared fixture files. Instruments default to the
    shared IDX seed when not overridden.
    """

    name = FIXTURE_SOURCE

    def __init__(
        self,
        instruments: list[RawInstrument] | None = None,
        bars: dict[str, list[RawBar]] | None = None,
        corporate_actions: dict[str, list[RawCorporateAction]] | None = None,
        calendar: list[RawCalendarDay] | None = None,
    ) -> None:
        self._instruments = instruments if instruments is not None else load_seed_instruments()
        self._bars = bars or {}
        self._corporate_actions = corporate_actions or {}
        self._calendar = calendar or []

    def get_instruments(self) -> list[RawInstrument]:
        return list(self._instruments)

    def get_daily_bars(self, source_symbol: str, start: date, end: date) -> list[RawBar]:
        bars = self._bars.get(source_symbol, [])
        return [bar for bar in bars if start <= bar.trade_date <= end]

    def get_corporate_actions(
        self, source_symbol: str, start: date, end: date
    ) -> list[RawCorporateAction]:
        actions = self._corporate_actions.get(source_symbol, [])
        return [action for action in actions if start <= action.ex_date <= end]

    def get_calendar(self, start: date, end: date) -> list[RawCalendarDay]:
        return [day for day in self._calendar if start <= day.date <= end]

    def get_latest_quote(self, source_symbol: str) -> RawBar | None:
        bars = self._bars.get(source_symbol, [])
        if not bars:
            return None
        return max(bars, key=lambda bar: bar.trade_date)
