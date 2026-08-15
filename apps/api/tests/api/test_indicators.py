from datetime import date

from app.db.enums import ListingStatus
from app.db.models import IndicatorSnapshot, Instrument


def _seed_instrument(db_session, symbol="BBCA"):
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


def test_list_instrument_indicators_404_for_unknown_symbol(client) -> None:
    response = client.get("/api/v1/instruments/NOPE/indicators")
    assert response.status_code == 404


def test_list_instrument_indicators_empty(client, db_session) -> None:
    _seed_instrument(db_session)
    response = client.get("/api/v1/instruments/BBCA/indicators")
    assert response.status_code == 200
    body = response.json()
    assert body == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_list_instrument_indicators_returns_seeded_rows(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id,
            trade_date=date(2024, 1, 2),
            indicator_version="v1",
            sma_20=100.5,
            rsi_14=55.2,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/instruments/BBCA/indicators")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["sma_20"] == 100.5
    assert body["items"][0]["rsi_14"] == 55.2


def test_list_instrument_indicators_filters_by_version(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id, trade_date=date(2024, 1, 2), indicator_version="v1"
        )
    )
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id,
            trade_date=date(2024, 1, 2),
            indicator_version="v2-experimental",
        )
    )
    db_session.commit()

    response = client.get("/api/v1/instruments/BBCA/indicators", params={"indicator_version": "v1"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_instrument_indicators_filters_by_date_range(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id, trade_date=date(2024, 1, 2), indicator_version="v1"
        )
    )
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id, trade_date=date(2024, 6, 2), indicator_version="v1"
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/instruments/BBCA/indicators",
        params={"start": "2024-01-01", "end": "2024-01-31"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_list_instrument_indicators_rejects_page_below_one(client, db_session) -> None:
    _seed_instrument(db_session)
    response = client.get("/api/v1/instruments/BBCA/indicators", params={"page": 0})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_instrument_indicators_rejects_page_size_over_max(client, db_session) -> None:
    _seed_instrument(db_session)
    response = client.get("/api/v1/instruments/BBCA/indicators", params={"page_size": 10_000})
    assert response.status_code == 422


def test_list_instrument_indicators_rejects_malformed_date(client, db_session) -> None:
    _seed_instrument(db_session)
    response = client.get("/api/v1/instruments/BBCA/indicators", params={"start": "not-a-date"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_instrument_indicators_unknown_version_returns_empty_not_error(
    client, db_session
) -> None:
    instrument = _seed_instrument(db_session)
    db_session.add(
        IndicatorSnapshot(
            instrument_id=instrument.id, trade_date=date(2024, 1, 2), indicator_version="v1"
        )
    )
    db_session.commit()

    response = client.get(
        "/api/v1/instruments/BBCA/indicators", params={"indicator_version": "v999-does-not-exist"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
