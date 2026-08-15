import json
import uuid
from datetime import date

import fakeredis
from sqlalchemy import select

from app.db.enums import AlertType
from app.db.models import Alert
from app.worker.alert_engine import AlertCandidate
from app.worker.alert_service import ALERTS_PUBSUB_CHANNEL, AlertService

TRIGGER_DATE = date(2024, 3, 1)


def _candidate(
    alert_type: AlertType = AlertType.SETUP_DETECTED, instrument_id: uuid.UUID | None = None
):
    return AlertCandidate(
        alert_type=alert_type,
        instrument_id=instrument_id or uuid.uuid4(),
        message="BBCA: setup detected",
        details={"symbol": "BBCA"},
    )


def test_persist_alerts_writes_new_alert(db_session) -> None:
    service = AlertService(db_session)
    candidate = _candidate()

    persisted = service.persist_alerts([candidate], TRIGGER_DATE)

    assert len(persisted) == 1
    row = db_session.scalar(select(Alert))
    assert row is not None
    assert row.alert_type == AlertType.SETUP_DETECTED


def test_persist_alerts_deduplicates_via_app_level_check(db_session) -> None:
    service = AlertService(db_session)
    candidate = _candidate(instrument_id=uuid.uuid4())

    first = service.persist_alerts([candidate], TRIGGER_DATE)
    second = service.persist_alerts([candidate], TRIGGER_DATE)

    assert len(first) == 1
    assert len(second) == 0
    assert len(db_session.scalars(select(Alert)).all()) == 1


def test_persist_alerts_deduplicates_via_db_constraint_on_concurrent_insert(db_session) -> None:
    """Simulates a concurrent duplicate slipping past the app-level
    check-then-insert: the DB unique constraint (not the check) is what
    must actually prevent the duplicate row."""
    service = AlertService(db_session)
    instrument_id = uuid.uuid4()
    candidate = _candidate(instrument_id=instrument_id)

    existing = Alert(
        alert_type=candidate.alert_type,
        instrument_id=instrument_id,
        trigger_date=TRIGGER_DATE,
        message="already here",
        details={},
    )
    db_session.add(existing)
    db_session.commit()

    persisted = service.persist_alerts([candidate], TRIGGER_DATE)

    assert persisted == []
    assert len(db_session.scalars(select(Alert)).all()) == 1


def test_persist_alerts_different_trigger_dates_are_independent(db_session) -> None:
    service = AlertService(db_session)
    instrument_id = uuid.uuid4()
    candidate = _candidate(instrument_id=instrument_id)

    service.persist_alerts([candidate], TRIGGER_DATE)
    service.persist_alerts([candidate], date(2024, 3, 2))

    assert len(db_session.scalars(select(Alert)).all()) == 2


def test_persist_alerts_publishes_to_redis_pubsub(db_session) -> None:
    redis = fakeredis.FakeRedis()
    pubsub = redis.pubsub()
    pubsub.subscribe(ALERTS_PUBSUB_CHANNEL)
    pubsub.get_message(timeout=1)  # discard the subscribe confirmation

    service = AlertService(db_session, redis)
    candidate = _candidate()
    service.persist_alerts([candidate], TRIGGER_DATE)

    message = pubsub.get_message(timeout=1)
    assert message is not None
    payload = json.loads(message["data"])
    assert payload["alert_type"] == AlertType.SETUP_DETECTED.value


def test_persist_alerts_without_redis_does_not_raise(db_session) -> None:
    service = AlertService(db_session, redis=None)
    persisted = service.persist_alerts([_candidate()], TRIGGER_DATE)

    assert len(persisted) == 1
