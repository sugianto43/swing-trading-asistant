import pytest

from app.scanner.cli import _parse_date, main


def test_parse_date() -> None:
    assert str(_parse_date("2024-06-01")) == "2024-06-01"


def test_main_requires_symbols_argument() -> None:
    with pytest.raises(SystemExit):
        main(["scan"])
