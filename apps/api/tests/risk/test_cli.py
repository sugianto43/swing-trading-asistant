import pytest

from app.risk.cli import _parse_date, main


def test_parse_date() -> None:
    assert str(_parse_date("2024-06-01")) == "2024-06-01"


def test_main_requires_symbol_argument() -> None:
    with pytest.raises(SystemExit):
        main(["plan", "--setup", "BREAKOUT", "--date", "2024-01-01", "--capital", "100000000"])


def test_main_rejects_invalid_setup_choice() -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "plan",
                "--symbol",
                "BBCA",
                "--setup",
                "NOT_REAL",
                "--date",
                "2024-01-01",
                "--capital",
                "100000000",
            ]
        )
