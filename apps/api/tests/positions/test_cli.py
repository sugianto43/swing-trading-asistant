import pytest

from app.positions.cli import _parse_datetime, main


def test_parse_datetime() -> None:
    dt = _parse_datetime("2024-06-01T10:30:00+00:00")
    assert dt.year == 2024
    assert dt.month == 6


def test_main_requires_symbol_argument() -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "record",
                "--side",
                "BUY",
                "--quantity",
                "10",
                "--price",
                "1000",
                "--executed-at",
                "2024-06-01T10:00:00+00:00",
            ]
        )


def test_main_rejects_invalid_side_choice() -> None:
    with pytest.raises(SystemExit):
        main(
            [
                "record",
                "--symbol",
                "BBCA",
                "--side",
                "NOT_REAL",
                "--quantity",
                "10",
                "--price",
                "1000",
                "--executed-at",
                "2024-06-01T10:00:00+00:00",
            ]
        )
