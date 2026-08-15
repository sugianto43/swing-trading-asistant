import pytest

from app.backtesting.cli import _parse_date, main


def test_parse_date() -> None:
    assert str(_parse_date("2024-06-01")) == "2024-06-01"


def test_main_requires_setup_argument() -> None:
    with pytest.raises(SystemExit):
        main(["run", "--start", "2024-01-01", "--end", "2024-06-01"])


def test_main_rejects_invalid_setup_choice() -> None:
    with pytest.raises(SystemExit):
        main(["run", "--setup", "NOT_REAL", "--start", "2024-01-01", "--end", "2024-06-01"])
