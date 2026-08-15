from app.indicators.cli import _parse_date, main


def test_parse_date() -> None:
    assert str(_parse_date("2024-01-02")) == "2024-01-02"


def test_main_requires_symbols_argument() -> None:
    import pytest

    with pytest.raises(SystemExit):
        main(["compute"])
