import pytest

from app.intelligence.cli import _parse_date, main


def test_parse_date() -> None:
    assert str(_parse_date("2024-06-01")) == "2024-06-01"


def test_main_requires_date_argument() -> None:
    with pytest.raises(SystemExit):
        main(["compute-breadth"])


def test_main_rejects_unknown_command() -> None:
    with pytest.raises(SystemExit):
        main(["not-a-real-command"])
