from datetime import UTC, date, datetime, timedelta

from app.db.enums import CorporateActionType, DataQualityStatus, ListingStatus
from app.db.models import CorporateAction, IndicatorSnapshot, Instrument, PriceBar

T0 = date(2024, 3, 1)


def _seed_instrument(db_session, symbol="BBCA", sector="Banking") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Bank Central Asia Tbk",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        sector=sector,
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def _seed_price_and_indicator(db_session, instrument, trade_date, close, sma_50=None) -> None:
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=trade_date,
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1_000_000,
            source="fixture",
            source_symbol=instrument.source_symbol,
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id,
            trade_date=trade_date,
            indicator_version="v1",
            sma_50=sma_50,
        )
    )
    db_session.commit()


def test_compute_breadth_endpoint(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, T0, close=110, sma_50=100)

    response = client.post("/api/v1/intelligence/breadth/compute", json={"as_of": str(T0)})
    assert response.status_code == 200
    body = response.json()
    assert body["universe_size"] == 1
    assert body["regime"] in {"RISK_ON", "RISK_OFF", "NEUTRAL"}


def test_get_breadth_404_when_none_computed(client) -> None:
    response = client.get("/api/v1/intelligence/breadth")
    assert response.status_code == 404


def test_get_breadth_returns_latest(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_price_and_indicator(db_session, instrument, T0, close=110, sma_50=100)
    client.post("/api/v1/intelligence/breadth/compute", json={"as_of": str(T0)})

    response = client.get("/api/v1/intelligence/breadth")
    assert response.status_code == 200
    assert response.json()["as_of"] == str(T0)


def test_breadth_history_pagination(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    for i in range(3):
        d = T0 + timedelta(days=i)
        _seed_price_and_indicator(db_session, instrument, d, close=100 + i, sma_50=100)
        client.post("/api/v1/intelligence/breadth/compute", json={"as_of": str(d)})

    response = client.get(
        "/api/v1/intelligence/breadth/history", params={"page": 1, "page_size": 2}
    )
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_sector_performance_endpoint(client, db_session) -> None:
    instrument = _seed_instrument(db_session, sector="Banking")
    _seed_price_and_indicator(db_session, instrument, T0 - timedelta(days=20), close=100)
    _seed_price_and_indicator(db_session, instrument, T0, close=110)

    response = client.get(
        "/api/v1/intelligence/sector-performance",
        params={"as_of": str(T0), "lookback_days": 20},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["sector"] == "Banking"


def test_sector_performance_requires_as_of(client) -> None:
    response = client.get("/api/v1/intelligence/sector-performance")
    assert response.status_code == 422


def test_sector_performance_lookback_days_boundary_rejects_zero(client) -> None:
    response = client.get(
        "/api/v1/intelligence/sector-performance",
        params={"as_of": str(T0), "lookback_days": 0},
    )
    assert response.status_code == 422


def test_sector_performance_lookback_days_boundary_rejects_over_365(client) -> None:
    response = client.get(
        "/api/v1/intelligence/sector-performance",
        params={"as_of": str(T0), "lookback_days": 366},
    )
    assert response.status_code == 422


def test_sector_performance_lookback_days_boundary_accepts_365(client, db_session) -> None:
    instrument = _seed_instrument(db_session, sector="Banking")
    _seed_price_and_indicator(db_session, instrument, T0 - timedelta(days=365), close=100)
    _seed_price_and_indicator(db_session, instrument, T0, close=110)
    response = client.get(
        "/api/v1/intelligence/sector-performance",
        params={"as_of": str(T0), "lookback_days": 365},
    )
    assert response.status_code == 200


def test_compute_breadth_invalid_date_format_rejected(client) -> None:
    response = client.post("/api/v1/intelligence/breadth/compute", json={"as_of": "not-a-date"})
    assert response.status_code == 422


def test_events_endpoint_returns_seeded_action(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=T0,
            announced_at=datetime(2024, 2, 1, tzinfo=UTC),
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/intelligence/events", params={"symbol": "BBCA"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["event_type"] == "SPLIT"
    assert body["items"][0]["symbol"] == "BBCA"


def test_events_endpoint_availability_leakage_filter(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=T0,
            announced_at=datetime(2024, 3, 5, tzinfo=UTC),
            ratio=2.0,
            source="fixture",
            source_symbol=instrument.source_symbol,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/intelligence/events", params={"symbol": "BBCA", "as_of": str(T0)}
    )
    assert response.json()["total"] == 0

    response = client.get(
        "/api/v1/intelligence/events",
        params={"symbol": "BBCA", "as_of": "2024-03-10"},
    )
    assert response.json()["total"] == 1


def test_events_endpoint_empty_for_unknown_symbol(client) -> None:
    response = client.get("/api/v1/intelligence/events", params={"symbol": "NOPE"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_events_endpoint_pagination(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    for i in range(3):
        db_session.add(
            CorporateAction(
                instrument_id=instrument.id,
                action_type=CorporateActionType.CASH_DIVIDEND,
                ex_date=T0 + timedelta(days=i),
                announced_at=datetime(2024, 2, 1 + i, tzinfo=UTC),
                amount=100.0 + i,
                source="fixture",
                source_symbol=instrument.source_symbol,
            )
        )
    db_session.commit()

    response = client.get(
        "/api/v1/intelligence/events",
        params={"symbol": "BBCA", "page": 1, "page_size": 2},
    )
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    response = client.get(
        "/api/v1/intelligence/events",
        params={"symbol": "BBCA", "page": 2, "page_size": 2},
    )
    assert len(response.json()["items"]) == 1
