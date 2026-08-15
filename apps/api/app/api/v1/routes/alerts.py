from collections.abc import Generator
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.pagination import MAX_PAGE_SIZE, Page
from app.api.v1.schemas.alerts import AlertOut
from app.db.enums import AlertType
from app.db.models import Alert, Instrument
from app.db.session import get_db
from app.worker.alert_service import ALERTS_PUBSUB_CHANNEL
from app.worker.queue import get_redis

router = APIRouter()

SSE_STREAM_TIMEOUT_SECONDS = 30  # how long a single blocking pubsub read waits before a keep-alive


@router.get("/alerts", response_model=Page[AlertOut])
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    alert_type: AlertType | None = None,
    symbol: str | None = None,
    trigger_date: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[AlertOut]:
    query = select(Alert)
    if alert_type is not None:
        query = query.where(Alert.alert_type == alert_type)
    if symbol is not None:
        query = query.join(Instrument, Alert.instrument_id == Instrument.id).where(
            Instrument.symbol == symbol
        )
    if trigger_date is not None:
        query = query.where(Alert.trigger_date == trigger_date)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(Alert.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Page[AlertOut](
        items=[AlertOut.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


def _sse_event_stream(redis: Redis) -> Generator[str, None, None]:
    pubsub = redis.pubsub()  # type: ignore[no-untyped-call]  # redis-py's pubsub() lacks a stub signature
    pubsub.subscribe(ALERTS_PUBSUB_CHANNEL)
    try:
        while True:
            message = pubsub.get_message(
                ignore_subscribe_messages=True, timeout=SSE_STREAM_TIMEOUT_SECONDS
            )
            if message is None:
                yield ": keep-alive\n\n"
                continue
            payload = message["data"]
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            yield f"data: {payload}\n\n"
    finally:
        pubsub.unsubscribe(ALERTS_PUBSUB_CHANNEL)
        pubsub.close()


@router.get("/alerts/stream")
def stream_alerts(redis: Annotated[Redis, Depends(get_redis)]) -> StreamingResponse:
    return StreamingResponse(_sse_event_stream(redis), media_type="text/event-stream")
