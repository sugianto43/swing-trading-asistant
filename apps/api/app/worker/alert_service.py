import json
from datetime import date

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Alert
from app.worker.alert_engine import AlertCandidate

ALERTS_PUBSUB_CHANNEL = "alerts:new"


class AlertService:
    """Persists AlertCandidates with deduplication backed by the DB's
    own unique constraint (alert_type, instrument_id, trigger_date) —
    the check-then-insert below is a fast path for the common case, but
    the constraint (not the check) is what actually guarantees no
    duplicate ever lands, including under concurrent job runs (the same
    IntegrityError-recovery pattern used since the Phase 6/7 fix-phase
    findings)."""

    def __init__(self, session: Session, redis: Redis | None = None):
        self.session = session
        self.redis = redis

    def persist_alerts(self, candidates: list[AlertCandidate], trigger_date: date) -> list[Alert]:
        persisted: list[Alert] = []
        for candidate in candidates:
            existing = self.session.scalar(
                select(Alert).where(
                    Alert.alert_type == candidate.alert_type,
                    Alert.instrument_id == candidate.instrument_id,
                    Alert.trigger_date == trigger_date,
                )
            )
            if existing is not None:
                continue  # already fired today for this instrument+type

            alert = Alert(
                alert_type=candidate.alert_type,
                instrument_id=candidate.instrument_id,
                trigger_date=trigger_date,
                message=candidate.message,
                details=candidate.details,
            )
            self.session.add(alert)
            try:
                self.session.commit()
            except IntegrityError:
                # a concurrent job run persisted the same alert in
                # between our SELECT and this INSERT — the constraint
                # caught it, which is the correct outcome (dedup held),
                # not an error to surface.
                self.session.rollback()
                continue

            self.session.refresh(alert)
            persisted.append(alert)
            self._publish(alert)

        return persisted

    def _publish(self, alert: Alert) -> None:
        if self.redis is None:
            return
        payload = {
            "id": str(alert.id),
            "alert_type": alert.alert_type.value,
            "instrument_id": str(alert.instrument_id),
            "trigger_date": alert.trigger_date.isoformat(),
            "message": alert.message,
        }
        try:
            self.redis.publish(ALERTS_PUBSUB_CHANNEL, json.dumps(payload))
        except RedisError:
            # the alert is already committed (source of truth); a broken
            # real-time broadcast must not fail persistence for this or
            # any remaining candidate in the batch, and must not surface
            # as a job failure for what's actually a successful persist.
            pass
