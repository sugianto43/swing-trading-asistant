from datetime import date

import pandas as pd
import pytest

from app.db.enums import CorporateActionType
from app.marketdata.provider import ProviderError
from app.marketdata.yfinance_provider import YfinanceProvider


class _FakeTicker:
    def __init__(self, history_df: pd.DataFrame, actions_df: pd.DataFrame | None = None):
        self._history_df = history_df
        self.actions = actions_df if actions_df is not None else pd.DataFrame()

    def history(self, **kwargs):
        return self._history_df


def _history_df() -> pd.DataFrame:
    index = pd.to_datetime(["2024-01-02", "2024-01-03"])
    return pd.DataFrame(
        {
            "Open": [9000.0, 9050.0],
            "High": [9100.0, 9200.0],
            "Low": [8950.0, 9000.0],
            "Close": [9050.0, 9150.0],
            "Volume": [1_000_000, 1_200_000],
        },
        index=index,
    )


def test_get_daily_bars_maps_dataframe_to_raw_bars(monkeypatch) -> None:
    import yfinance as yf

    monkeypatch.setattr(yf, "Ticker", lambda symbol: _FakeTicker(_history_df()))

    provider = YfinanceProvider()
    bars = provider.get_daily_bars("BBCA.JK", date(2024, 1, 1), date(2024, 1, 31))

    assert len(bars) == 2
    assert bars[0].trade_date == date(2024, 1, 2)
    assert bars[0].close == 9050.0
    assert bars[0].previous_close is None
    assert bars[1].previous_close == 9050.0
    assert bars[1].change == 100.0


def test_get_daily_bars_converts_tz_aware_index_to_canonical_timezone(monkeypatch) -> None:
    import yfinance as yf

    # 2024-01-02 20:00 UTC is 2024-01-03 03:00 in Asia/Jakarta (UTC+7) — a
    # naive ".date()" on the UTC timestamp would wrongly report 2024-01-02.
    index = pd.to_datetime(["2024-01-02 20:00"]).tz_localize("UTC")
    history_df = pd.DataFrame(
        {"Open": [100.0], "High": [105.0], "Low": [95.0], "Close": [102.0], "Volume": [1000]},
        index=index,
    )
    monkeypatch.setattr(yf, "Ticker", lambda symbol: _FakeTicker(history_df))

    provider = YfinanceProvider()
    bars = provider.get_daily_bars("BBCA.JK", date(2024, 1, 1), date(2024, 1, 31))

    assert bars[0].trade_date == date(2024, 1, 3)


def test_get_daily_bars_wraps_provider_errors(monkeypatch) -> None:
    import yfinance as yf

    class _BrokenTicker:
        def history(self, **kwargs):
            raise RuntimeError("network down")

    monkeypatch.setattr(yf, "Ticker", lambda symbol: _BrokenTicker())

    provider = YfinanceProvider()
    with pytest.raises(ProviderError):
        provider.get_daily_bars("BBCA.JK", date(2024, 1, 1), date(2024, 1, 31))


def test_get_corporate_actions_maps_dividends_and_splits(monkeypatch) -> None:
    import yfinance as yf

    actions_index = pd.to_datetime(["2024-01-15", "2024-02-01"])
    actions_df = pd.DataFrame(
        {"Dividends": [50.0, 0.0], "Stock Splits": [0.0, 2.0]}, index=actions_index
    )
    monkeypatch.setattr(yf, "Ticker", lambda symbol: _FakeTicker(_history_df(), actions_df))

    provider = YfinanceProvider()
    results = provider.get_corporate_actions("BBCA.JK", date(2024, 1, 1), date(2024, 12, 31))

    assert len(results) == 2
    dividend = next(r for r in results if r.action_type == CorporateActionType.CASH_DIVIDEND)
    assert dividend.amount == 50.0
    split = next(r for r in results if r.action_type == CorporateActionType.SPLIT)
    assert split.ratio == 2.0


def test_get_calendar_returns_empty_documented_limitation() -> None:
    provider = YfinanceProvider()
    assert provider.get_calendar(date(2024, 1, 1), date(2024, 1, 31)) == []


def test_get_instruments_uses_local_seed_not_vendor_api() -> None:
    provider = YfinanceProvider()
    instruments = provider.get_instruments()
    assert len(instruments) == 10
    assert all(i.source == "idx-seed" for i in instruments)
