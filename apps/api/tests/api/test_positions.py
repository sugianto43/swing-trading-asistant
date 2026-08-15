import uuid
from datetime import datetime

from app.db.enums import ListingStatus, SetupType, TradePlanStatus
from app.db.models import Instrument, TradePlan

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


def _seed_trade_plan(db_session, instrument, status=TradePlanStatus.VALID) -> TradePlan:
    plan = TradePlan(
        instrument_id=instrument.id,
        setup_type=SetupType.BREAKOUT,
        plan_date=datetime.fromisoformat(T0).date(),
        risk_version="v1",
        status=status,
        rejection_reasons=[],
        entry_price=1000.0,
        stop_price=950.0,
        target_prices=[1100.0],
        quantity=100,
        allocation_amount=100_000.0,
        allocation_pct=0.1,
        max_loss_amount=5_000.0,
        assumptions={"capital": 1_000_000.0},
        invalidation_conditions=[],
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def test_record_execution_creates_position(client, db_session) -> None:
    _seed_instrument(db_session)
    response = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 50.0,
            "executed_at": T0,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["quantity_open"] == 100


def test_record_execution_unknown_symbol_404(client) -> None:
    response = client.post(
        "/api/v1/executions",
        json={
            "symbol": "NOPE",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_record_execution_oversell_returns_409(client, db_session) -> None:
    _seed_instrument(db_session)
    client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 50,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    )
    response = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "SELL",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T1,
        },
    )
    assert response.status_code == 409


def test_record_execution_invalid_quantity_rejected_by_validation(client) -> None:
    response = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 0,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_record_execution_negative_fee_rejected_by_validation(client) -> None:
    response = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 10,
            "price": 1000.0,
            "fee": -1.0,
            "executed_at": T0,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_record_execution_invalid_side_rejected_by_validation(client) -> None:
    response = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "SHORT",
            "quantity": 10,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_journal_reference_urls_over_max_length_rejected(client, db_session) -> None:
    _seed_instrument(db_session)
    position = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    ).json()
    response = client.post(
        f"/api/v1/positions/{position['id']}/journal",
        json={"reference_urls": [f"https://example.com/{i}.png" for i in range(51)]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_executions_filters_by_position_id(client, db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA")
    _seed_instrument(db_session, symbol="BBRI")
    position_a = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    ).json()
    client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBRI",
            "side": "BUY",
            "quantity": 50,
            "price": 500.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    )
    response = client.get("/api/v1/executions", params={"position_id": position_a["id"]})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["position_id"] == position_a["id"]


def test_list_executions_pagination(client, db_session) -> None:
    _seed_instrument(db_session)
    for _i in range(3):
        client.post(
            "/api/v1/executions",
            json={
                "symbol": "BBCA",
                "side": "BUY",
                "quantity": 10,
                "price": 1000.0,
                "fee": 0.0,
                "executed_at": T0,
            },
        )
    response = client.get("/api/v1/executions", params={"page": 1, "page_size": 2})
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    response = client.get("/api/v1/executions", params={"page": 2, "page_size": 2})
    body = response.json()
    assert len(body["items"]) == 1


def test_list_executions_filters_by_symbol(client, db_session) -> None:
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
    response = client.get("/api/v1/executions", params={"symbol": "BBCA"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get("/api/v1/executions", params={"symbol": "NONE"})
    assert response.json()["total"] == 0


def test_create_planned_position(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument)
    response = client.post("/api/v1/positions", json={"trade_plan_id": str(plan.id)})
    assert response.status_code == 201
    assert response.json()["status"] == "PLANNED"


def test_create_planned_position_from_rejected_plan_409(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument, status=TradePlanStatus.REJECTED)
    response = client.post("/api/v1/positions", json={"trade_plan_id": str(plan.id)})
    assert response.status_code == 409


def test_create_planned_position_unknown_plan_404(client) -> None:
    response = client.post("/api/v1/positions", json={"trade_plan_id": str(uuid.uuid4())})
    assert response.status_code == 404


def test_cancel_planned_position(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    plan = _seed_trade_plan(db_session, instrument)
    created = client.post("/api/v1/positions", json={"trade_plan_id": str(plan.id)}).json()
    response = client.post(f"/api/v1/positions/{created['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_cancel_open_position_409(client, db_session) -> None:
    _seed_instrument(db_session)
    created = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    ).json()
    response = client.post(f"/api/v1/positions/{created['id']}/cancel")
    assert response.status_code == 409


def test_list_positions_filters_by_status(client, db_session) -> None:
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
    response = client.get("/api/v1/positions", params={"status": "OPEN"})
    assert response.json()["total"] == 1
    response = client.get("/api/v1/positions", params={"status": "CLOSED"})
    assert response.json()["total"] == 0


def test_get_position_404_for_unknown_id(client) -> None:
    response = client.get(f"/api/v1/positions/{uuid.uuid4()}")
    assert response.status_code == 404


def test_journal_upsert_and_get(client, db_session) -> None:
    _seed_instrument(db_session)
    position = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    ).json()

    response = client.post(
        f"/api/v1/positions/{position['id']}/journal",
        json={"thesis": "breakout thesis", "reference_urls": ["https://example.com/x.png"]},
    )
    assert response.status_code == 200
    assert response.json()["thesis"] == "breakout thesis"

    response = client.get(f"/api/v1/positions/{position['id']}/journal")
    assert response.status_code == 200
    assert response.json()["thesis"] == "breakout thesis"


def test_get_journal_404_when_absent(client, db_session) -> None:
    _seed_instrument(db_session)
    position = client.post(
        "/api/v1/executions",
        json={
            "symbol": "BBCA",
            "side": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "fee": 0.0,
            "executed_at": T0,
        },
    ).json()
    response = client.get(f"/api/v1/positions/{position['id']}/journal")
    assert response.status_code == 404
