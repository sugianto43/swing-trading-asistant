from datetime import date

from app.db.enums import CorporateActionType
from app.marketdata.fixture_provider import FixtureProvider
from app.marketdata.provider import RawBar, RawCorporateAction


def test_fixture_provider_satisfies_protocol_shape() -> None:
    provider = FixtureProvider()
    assert provider.name == "fixture"
    assert callable(provider.get_instruments)
    assert callable(provider.get_daily_bars)
    assert callable(provider.get_corporate_actions)
    assert callable(provider.get_calendar)
    assert callable(provider.get_latest_quote)


def test_fixture_provider_defaults_to_seed_instruments() -> None:
    provider = FixtureProvider()
    instruments = provider.get_instruments()
    symbols = {i.symbol for i in instruments}
    assert "BBCA" in symbols
    assert len(instruments) == 10


def test_fixture_provider_filters_bars_by_date_range() -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 100, 105, 95, 102, 1000, "fixture"),
            RawBar("BBCA.JK", date(2024, 2, 2), 110, 115, 105, 112, 1000, "fixture"),
        ]
    }
    provider = FixtureProvider(bars=bars)
    result = provider.get_daily_bars("BBCA.JK", date(2024, 1, 1), date(2024, 1, 31))
    assert len(result) == 1
    assert result[0].trade_date == date(2024, 1, 2)


def test_fixture_provider_get_latest_quote_returns_most_recent_bar() -> None:
    bars = {
        "BBCA.JK": [
            RawBar("BBCA.JK", date(2024, 1, 2), 100, 105, 95, 102, 1000, "fixture"),
            RawBar("BBCA.JK", date(2024, 1, 5), 110, 115, 105, 112, 1000, "fixture"),
        ]
    }
    provider = FixtureProvider(bars=bars)
    quote = provider.get_latest_quote("BBCA.JK")
    assert quote is not None
    assert quote.trade_date == date(2024, 1, 5)


def test_fixture_provider_get_latest_quote_none_when_no_bars() -> None:
    provider = FixtureProvider(bars={})
    assert provider.get_latest_quote("UNKNOWN.JK") is None


def test_fixture_provider_corporate_actions_filtered_by_range() -> None:
    actions = {
        "BBCA.JK": [
            RawCorporateAction(
                "BBCA.JK",
                CorporateActionType.CASH_DIVIDEND,
                date(2024, 1, 15),
                "fixture",
                amount=50,
            ),
            RawCorporateAction(
                "BBCA.JK", CorporateActionType.SPLIT, date(2024, 6, 1), "fixture", ratio=2.0
            ),
        ]
    }
    provider = FixtureProvider(corporate_actions=actions)
    result = provider.get_corporate_actions("BBCA.JK", date(2024, 1, 1), date(2024, 3, 1))
    assert len(result) == 1
    assert result[0].action_type == CorporateActionType.CASH_DIVIDEND
