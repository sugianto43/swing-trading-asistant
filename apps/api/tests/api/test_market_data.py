from datetime import date

from app.db.enums import CorporateActionType, DataQualityStatus, ListingStatus
from app.db.models import CorporateAction, Instrument, PriceBar, TradingCalendarDay


def _seed_instrument(db_session, symbol="BBCA", sector="Financials", status=ListingStatus.ACTIVE):
    instrument = Instrument(
        symbol=symbol,
        company_name="Bank Central Asia Tbk",
        exchange="IDX",
        currency="IDR",
        security_type="EQUITY",
        sector=sector,
        subsector="Banks",
        status=status,
        source="fixture",
        source_symbol=f"{symbol}.JK",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def test_list_instruments_empty(client) -> None:
    response = client.get("/api/v1/instruments")
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_list_instruments_returns_seeded_rows(client, db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA")
    _seed_instrument(db_session, symbol="BBRI")

    response = client.get("/api/v1/instruments")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["symbol"] for item in body["items"]} == {"BBCA", "BBRI"}


def test_list_instruments_filters_by_sector(client, db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA", sector="Financials")
    _seed_instrument(db_session, symbol="TLKM", sector="Infrastructure")

    response = client.get("/api/v1/instruments", params={"sector": "Financials"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "BBCA"


def test_list_instruments_pagination(client, db_session) -> None:
    for i in range(5):
        _seed_instrument(db_session, symbol=f"SYM{i}")

    response = client.get("/api/v1/instruments", params={"page": 2, "page_size": 2})

    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2


def test_get_instrument_detail(client, db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA")

    response = client.get("/api/v1/instruments/BBCA")

    assert response.status_code == 200
    assert response.json()["symbol"] == "BBCA"


def test_get_instrument_detail_is_case_insensitive(client, db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA")

    response = client.get("/api/v1/instruments/bbca")

    assert response.status_code == 200


def test_get_instrument_detail_404_uses_error_envelope(client) -> None:
    response = client.get("/api/v1/instruments/NOPE")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "HTTP_ERROR", "message": "instrument not found", "details": None}
    }


def test_list_instrument_prices(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=date(2024, 1, 2),
            open=9000,
            high=9100,
            low=8950,
            close=9050,
            volume=1_000_000,
            source="fixture",
            source_symbol="BBCA.JK",
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/instruments/BBCA/prices")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["close"] == 9050.0


def test_list_instrument_prices_404_for_unknown_symbol(client) -> None:
    response = client.get("/api/v1/instruments/NOPE/prices")
    assert response.status_code == 404


def test_list_instrument_prices_adjusted_applies_split(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=date(2024, 1, 2),
            open=2000,
            high=2000,
            low=2000,
            close=2000,
            volume=1000,
            source="fixture",
            source_symbol="BBCA.JK",
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.SPLIT,
            ex_date=date(2024, 2, 1),
            source="fixture",
            source_symbol="BBCA.JK",
            ratio=2.0,
        )
    )
    db_session.commit()

    raw_response = client.get("/api/v1/instruments/BBCA/prices")
    adjusted_response = client.get("/api/v1/instruments/BBCA/prices", params={"adjusted": "true"})

    assert raw_response.json()["items"][0]["close"] == 2000.0
    assert adjusted_response.json()["items"][0]["close"] == 1000.0


def test_list_instrument_corporate_actions(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        CorporateAction(
            instrument_id=instrument.id,
            action_type=CorporateActionType.CASH_DIVIDEND,
            ex_date=date(2024, 3, 1),
            source="fixture",
            source_symbol="BBCA.JK",
            amount=50.0,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/instruments/BBCA/corporate-actions")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["amount"] == 50.0


def test_list_calendar_days(client, db_session) -> None:
    db_session.add(
        TradingCalendarDay(date=date(2024, 1, 2), is_trading_day=True, source="observed")
    )
    db_session.add(
        TradingCalendarDay(date=date(2024, 1, 6), is_trading_day=False, source="observed")
    )
    db_session.commit()

    response = client.get("/api/v1/calendar", params={"start": "2024-01-01", "end": "2024-01-31"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2


def test_list_instruments_rejects_page_below_one(client) -> None:
    response = client.get("/api/v1/instruments", params={"page": 0})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_instruments_rejects_page_size_over_max(client) -> None:
    response = client.get("/api/v1/instruments", params={"page_size": 10_000})
    assert response.status_code == 422


def test_list_instrument_prices_rejects_malformed_date(client, db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA")
    response = client.get("/api/v1/instruments/BBCA/prices", params={"start": "not-a-date"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_instruments_unknown_sector_returns_empty_not_error(client, db_session) -> None:
    _seed_instrument(db_session, symbol="BBCA", sector="Financials")
    response = client.get("/api/v1/instruments", params={"sector": "NoSuchSector"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_instrument_prices_start_after_end_returns_empty(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        PriceBar(
            instrument_id=instrument.id,
            trade_date=date(2024, 1, 2),
            open=9000,
            high=9100,
            low=8950,
            close=9050,
            volume=1_000_000,
            source="fixture",
            source_symbol="BBCA.JK",
            quality_status=DataQualityStatus.VALID,
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/instruments/BBCA/prices",
        params={"start": "2024-06-01", "end": "2024-01-01"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
