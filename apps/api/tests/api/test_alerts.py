from datetime import UTC, date, datetime

from app.db.enums import AlertType, ListingStatus
from app.db.models import Alert, Instrument, InstrumentStatusHistory
from app.main import app

TRIGGER_DATE = date(2024, 3, 1)


def _seed_instrument(db_session, symbol: str = "BBCA") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Test Co",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        sector="Banking",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.flush()
    db_session.add(
        InstrumentStatusHistory(
            instrument_id=instrument.id,
            status=ListingStatus.ACTIVE,
            effective_from=datetime(2020, 1, 1, tzinfo=UTC),
            source="fixture",
        )
    )
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_alert(
    db_session, instrument: Instrument, alert_type: AlertType = AlertType.SETUP_DETECTED
) -> Alert:
    alert = Alert(
        alert_type=alert_type,
        instrument_id=instrument.id,
        trigger_date=TRIGGER_DATE,
        message=f"{instrument.symbol}: {alert_type.value}",
        details={},
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


def test_list_alerts_empty(client) -> None:
    response = client.get("/api/v1/alerts")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_alerts_returns_persisted_alerts(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_alert(db_session, instrument)

    response = client.get("/api/v1/alerts")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["alert_type"] == AlertType.SETUP_DETECTED.value


def test_list_alerts_filters_by_alert_type(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_alert(db_session, instrument, alert_type=AlertType.SETUP_DETECTED)
    _seed_alert(db_session, instrument, alert_type=AlertType.STALE_DATA)

    response = client.get("/api/v1/alerts", params={"alert_type": "STALE_DATA"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["alert_type"] == AlertType.STALE_DATA.value


def test_list_alerts_filters_by_symbol(client, db_session) -> None:
    bbca = _seed_instrument(db_session, symbol="BBCA")
    tlkm = _seed_instrument(db_session, symbol="TLKM")
    _seed_alert(db_session, bbca)
    _seed_alert(db_session, tlkm)

    response = client.get("/api/v1/alerts", params={"symbol": "TLKM"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["message"].startswith("TLKM")


def test_list_alerts_filters_by_trigger_date(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_alert(db_session, instrument)

    response = client.get("/api/v1/alerts", params={"trigger_date": "2024-03-02"})

    body = response.json()
    assert body["total"] == 0


def test_stream_alerts_route_is_registered() -> None:
    """The SSE generator blocks on a real Redis pubsub read, which isn't
    practical to drive to completion in-process (fakeredis's pubsub
    timeout semantics don't reliably unblock it) — so this only verifies
    the route is wired up; the live end-to-end path is exercised manually
    against real Redis at sign-off."""
    schema = app.openapi()
    assert "get" in schema["paths"]["/api/v1/alerts/stream"]
