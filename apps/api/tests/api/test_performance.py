from app.db.enums import ListingStatus
from app.db.models import Instrument

T0 = "2024-01-01T00:00:00+00:00"
T1 = "2024-01-10T00:00:00+00:00"


def _seed_instrument(db_session, symbol="BBCA") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Bank Central Asia Tbk",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        status=ListingStatus.ACTIVE,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def test_performance_summary_empty(client) -> None:
    response = client.get("/api/v1/performance/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["closed_position_count"] == 0
    assert body["equity_curve"] == []


def test_performance_summary_after_closed_trade(client, db_session) -> None:
    _seed_instrument(db_session)
    client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    )
    client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "SELL",
            "quantity": 100,
            "price": 1100.0,
            "fee": 0.0,
            "executed_at": T1,
        },
    )
    response = client.get("/api/v1/performance/summary")
    body = response.json()
    assert body["closed_position_count"] == 1
    assert body["total_realized_pnl"] == 10_000.0
    assert len(body["equity_curve"]) == 1


def test_performance_by_setup_empty(client) -> None:
    response = client.get("/api/v1/performance/by-setup")
    assert response.status_code == 200
    assert response.json() == []


def test_performance_by_sector_after_trade(client, db_session) -> None:
    _seed_instrument(db_session)
    client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    )
    client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "SELL",
            "quantity": 100,
            "price": 1100.0,
            "fee": 0.0,
            "executed_at": T1,
        },
    )
    response = client.get("/api/v1/performance/by-sector")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_performance_behavior_empty(client) -> None:
    response = client.get("/api/v1/performance/behavior")
    assert response.status_code == 200
    assert response.json() == []
