import pytest

from app.ai.cli import main


def test_main_requires_question_argument() -> None:
    with pytest.raises(SystemExit):
        main(["analyze", "--symbol", "BBCA"])


def test_main_rejects_unknown_command() -> None:
    with pytest.raises(SystemExit):
        main(["not-a-real-command"])
