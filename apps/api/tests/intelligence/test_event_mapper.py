import uuid
from datetime import UTC, date, datetime

from app.db.enums import CorporateActionType
from app.db.models import CorporateAction
from app.intelligence.event_mapper import corporate_action_to_event


def _corporate_action(**overrides) -> CorporateAction:
    defaults = dict(
        instrument_id=uuid.uuid4(),
        action_type=CorporateActionType.SPLIT,
        ex_date=date(2024, 3, 1),
        effective_date=date(2024, 3, 2),
        announced_at=datetime(2024, 2, 15, tzinfo=UTC),
        ratio=2.0,
        amount=None,
        source="fixture",
        source_symbol="BBCA.JK",
        ingested_at=datetime(2024, 2, 20, tzinfo=UTC),
    )
    defaults.update(overrides)
    return CorporateAction(**defaults)


def test_mapper_uses_announced_at_when_present() -> None:
    ca = _corporate_action()
    event = corporate_action_to_event(ca)
    assert event.announced_at == datetime(2024, 2, 15, tzinfo=UTC)
    assert event.availability_is_estimated is False


def test_mapper_falls_back_to_ingested_at_when_announced_at_missing() -> None:
    ca = _corporate_action(announced_at=None)
    event = corporate_action_to_event(ca)
    assert event.announced_at == datetime(2024, 2, 20, tzinfo=UTC)
    assert event.availability_is_estimated is True


def test_mapper_preserves_ex_date_and_effective_date() -> None:
    ca = _corporate_action()
    event = corporate_action_to_event(ca)
    assert event.ex_date == date(2024, 3, 1)
    assert event.effective_date == date(2024, 3, 2)


def test_mapper_description_includes_ratio() -> None:
    ca = _corporate_action(ratio=3.0)
    event = corporate_action_to_event(ca)
    assert "ratio=3.0" in event.description


def test_mapper_description_includes_amount_for_dividends() -> None:
    ca = _corporate_action(action_type=CorporateActionType.CASH_DIVIDEND, ratio=None, amount=150.0)
    event = corporate_action_to_event(ca)
    assert "amount=150.0" in event.description
    assert event.event_type == "CASH_DIVIDEND"
