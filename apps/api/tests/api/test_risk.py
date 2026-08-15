import uuid
from datetime import UTC, date, datetime, timedelta

from app.db.enums import DataQualityStatus, ListingStatus, SetupType
from app.db.models import (
    IndicatorSnapshot,
    Instrument,
    InstrumentStatusHistory,
    PriceBar,
    ScanCandidate,
)
from app.indicators.versioning import INDICATOR_VERSION
from app.scanner.scoring_config import SCORE_VERSION

PLAN_DATE = date(2024, 3, 1)


def _seed_instrument(db_session, symbol="BBCA") -> Instrument:
    instrument = Instrument(
        symbol=symbol,
        company_name="Bank Central Asia Tbk",
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


def _seed_tradeable_setup(db_session, instrument: Instrument) -> None:
    for i in range(5):
        trade_date = PLAN_DATE - timedelta(days=4 - i)
        db_session.add(
            PriceBar(
                instrument_id=instrument.id,
                trade_date=trade_date,
                open=1000.0,
                high=1010.0,
                low=990.0,
                close=1000.0,
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
                indicator_version=INDICATOR_VERSION,
                atr_14=20.0,
                volume_sma_20=1_000_000.0,
            )
        )
    db_session.add(
        ScanCandidate(
            instrument_id=instrument.id,
            scan_date=PLAN_DATE,
            setup_type=SetupType.BREAKOUT,
            indicator_version=INDICATOR_VERSION,
            score_version=SCORE_VERSION,
            composite_score=80.0,
            trend_score=0,
            momentum_score=0,
            volume_score=0,
            price_structure_score=0,
            volatility_score=0,
            setup_quality_score=0,
            risk_reward_score=0,
            qualifying_conditions=["test"],
            invalidation_conditions=["test"],
        )
    )
    db_session.commit()


def test_list_trade_plans_empty(client) -> None:
    response = client.get("/api/v1/risk/trade-plans")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_create_trade_plan_valid(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_setup(db_session, instrument)

    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": 100_000_000.0,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "VALID"
    assert body["quantity"] > 0
    assert len(body["target_prices"]) == 2


def test_create_trade_plan_unknown_symbol_404(client) -> None:
    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "NOPE",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": 100_000_000.0,
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_create_trade_plan_invalid_capital_rejected_by_validation(client) -> None:
    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": -1.0,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_trade_plan_zero_capital_rejected_by_validation(client) -> None:
    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": 0.0,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_trade_plan_invalid_setup_type_rejected_by_validation(client) -> None:
    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "NOT_A_REAL_SETUP",
            "plan_date": str(PLAN_DATE),
            "capital": 100_000_000.0,
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_trade_plan_negative_existing_allocation_rejected_by_validation(client) -> None:
    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": 100_000_000.0,
            "existing_positions": [{"symbol": "OTHER", "sector": None, "allocation_amount": -1.0}],
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_trade_plan_with_existing_portfolio_rejects_on_concentration(
    client, db_session
) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_setup(db_session, instrument)

    response = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": 100_000_000.0,
            "existing_positions": [
                {"symbol": "OTHER", "sector": "Banking", "allocation_amount": 95_000_000.0}
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "REJECTED"
    assert any("exposure" in r for r in body["rejection_reasons"])


def test_list_trade_plans_filters_by_symbol(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_setup(db_session, instrument)
    client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": 100_000_000.0,
        },
    )

    response = client.get("/api/v1/risk/trade-plans", params={"symbol": "BBCA"})
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = client.get("/api/v1/risk/trade-plans", params={"symbol": "NONE"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_get_trade_plan_404_for_unknown_id(client) -> None:
    response = client.get(f"/api/v1/risk/trade-plans/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_trade_plan_returns_created_plan(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_tradeable_setup(db_session, instrument)
    created = client.post(
        "/api/v1/risk/trade-plans",
        json={
            "symbol": "BBCA",
            "setup_type": "BREAKOUT",
            "plan_date": str(PLAN_DATE),
            "capital": 100_000_000.0,
        },
    ).json()

    response = client.get(f"/api/v1/risk/trade-plans/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
