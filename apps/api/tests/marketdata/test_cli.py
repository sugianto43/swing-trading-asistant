from app.marketdata.cli import _build_provider
from app.marketdata.fixture_provider import FixtureProvider


def test_build_provider_fixture() -> None:
    provider = _build_provider("fixture")
    assert isinstance(provider, FixtureProvider)


def test_build_provider_yfinance() -> None:
    from app.marketdata.yfinance_provider import YfinanceProvider

    provider = _build_provider("yfinance")
    assert isinstance(provider, YfinanceProvider)


def test_build_provider_unknown_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown provider"):
        _build_provider("bogus")
