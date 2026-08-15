from datetime import date

from app.db.enums import ListingStatus, SetupType
from app.db.models import Instrument, ScanCandidate


def _seed_instrument(db_session, symbol="BBCA", sector="Financials"):
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


def _seed_candidate(db_session, instrument, scan_date=date(2024, 6, 1), **overrides):
    defaults = {
        "instrument_id": instrument.id,
        "scan_date": scan_date,
        "setup_type": SetupType.MOMENTUM_CONTINUATION,
        "indicator_version": "v1",
        "score_version": "v1",
        "composite_score": 75.0,
        "trend_score": 80.0,
        "momentum_score": 70.0,
        "volume_score": 60.0,
        "price_structure_score": 65.0,
        "volatility_score": 90.0,
        "setup_quality_score": 70.0,
        "risk_reward_score": 50.0,
        "qualifying_conditions": ["example condition"],
        "invalidation_conditions": ["example invalidation"],
    }
    defaults.update(overrides)
    candidate = ScanCandidate(**defaults)
    db_session.add(candidate)
    db_session.commit()
    return candidate


def test_list_scan_candidates_empty(client) -> None:
    response = client.get("/api/v1/scanner/candidates")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_list_scan_candidates_returns_seeded_rows(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(db_session, instrument)

    response = client.get("/api/v1/scanner/candidates")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "BBCA"
    assert body["items"][0]["setup_type"] == "MOMENTUM_CONTINUATION"


def test_list_scan_candidates_filters_by_sector(client, db_session) -> None:
    financial = _seed_instrument(db_session, "BBCA", sector="Financials")
    infra = _seed_instrument(db_session, "TLKM", sector="Infrastructure")
    _seed_candidate(db_session, financial)
    _seed_candidate(db_session, infra)

    response = client.get("/api/v1/scanner/candidates", params={"sector": "Financials"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "BBCA"


def test_list_scan_candidates_filters_by_setup(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(db_session, instrument, setup_type=SetupType.BREAKOUT)
    _seed_candidate(
        db_session,
        instrument,
        setup_type=SetupType.MOMENTUM_CONTINUATION,
        scan_date=date(2024, 6, 2),
    )

    response = client.get("/api/v1/scanner/candidates", params={"setup": "BREAKOUT"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["setup_type"] == "BREAKOUT"


def test_list_scan_candidates_filters_by_min_score(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(db_session, instrument, composite_score=40.0)

    response = client.get("/api/v1/scanner/candidates", params={"min_score": 50.0})

    assert response.json()["total"] == 0


def test_list_scan_candidates_sorts_by_score_desc_by_default(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(
        db_session,
        instrument,
        setup_type=SetupType.BREAKOUT,
        composite_score=30.0,
    )
    _seed_candidate(
        db_session,
        instrument,
        setup_type=SetupType.MOMENTUM_CONTINUATION,
        composite_score=90.0,
    )

    response = client.get("/api/v1/scanner/candidates")

    scores = [item["composite_score"] for item in response.json()["items"]]
    assert scores == sorted(scores, reverse=True)


def test_list_scan_candidates_rejects_invalid_sort(client) -> None:
    response = client.get("/api/v1/scanner/candidates", params={"sort": "bogus"})
    assert response.status_code == 422


def test_list_scan_candidates_rejects_page_below_one(client) -> None:
    response = client.get("/api/v1/scanner/candidates", params={"page": 0})
    assert response.status_code == 422


def test_list_instrument_candidates_404_for_unknown_symbol(client) -> None:
    response = client.get("/api/v1/instruments/NOPE/candidates")
    assert response.status_code == 404


def test_list_instrument_candidates_returns_seeded_rows(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(db_session, instrument)

    response = client.get("/api/v1/instruments/BBCA/candidates")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "BBCA"


def test_list_scan_candidates_rejects_invalid_setup_enum(client) -> None:
    response = client.get("/api/v1/scanner/candidates", params={"setup": "NOT_A_REAL_SETUP"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_scan_candidates_rejects_malformed_scan_date(client) -> None:
    response = client.get("/api/v1/scanner/candidates", params={"scan_date": "not-a-date"})
    assert response.status_code == 422


def test_list_scan_candidates_rejects_page_size_over_max(client) -> None:
    response = client.get("/api/v1/scanner/candidates", params={"page_size": 10_000})
    assert response.status_code == 422


def test_list_scan_candidates_unknown_sector_returns_empty_not_error(client, db_session) -> None:
    instrument = _seed_instrument(db_session, sector="Financials")
    _seed_candidate(db_session, instrument)

    response = client.get("/api/v1/scanner/candidates", params={"sector": "NoSuchSector"})

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_scan_candidates_filters_by_scan_date(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(db_session, instrument, scan_date=date(2024, 6, 1))
    _seed_candidate(
        db_session, instrument, scan_date=date(2024, 6, 2), setup_type=SetupType.BREAKOUT
    )

    response = client.get("/api/v1/scanner/candidates", params={"scan_date": "2024-06-01"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["scan_date"] == "2024-06-01"


def test_list_scan_candidates_sort_by_momentum(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(db_session, instrument, setup_type=SetupType.BREAKOUT, momentum_score=20.0)
    _seed_candidate(
        db_session, instrument, setup_type=SetupType.MOMENTUM_CONTINUATION, momentum_score=90.0
    )

    response = client.get("/api/v1/scanner/candidates", params={"sort": "momentum"})

    momentum_scores = [item["momentum_score"] for item in response.json()["items"]]
    assert momentum_scores == sorted(momentum_scores, reverse=True)


def test_list_scan_candidates_sort_by_volume_score(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_candidate(db_session, instrument, setup_type=SetupType.BREAKOUT, volume_score=20.0)
    _seed_candidate(
        db_session, instrument, setup_type=SetupType.MOMENTUM_CONTINUATION, volume_score=90.0
    )

    response = client.get("/api/v1/scanner/candidates", params={"sort": "volume_score"})

    volume_scores = [item["volume_score"] for item in response.json()["items"]]
    assert volume_scores == sorted(volume_scores, reverse=True)


def test_list_scan_candidates_rejects_old_relative_volume_sort_key(client) -> None:
    # renamed to volume_score for honesty about what it sorts by
    response = client.get("/api/v1/scanner/candidates", params={"sort": "relative_volume"})
    assert response.status_code == 422
