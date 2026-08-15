import uuid

from app.ai.config import PROMPT_VERSION
from app.db.enums import ListingStatus
from app.db.models import AnalysisSnapshot, Instrument


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


def _seed_snapshot(db_session, instrument=None) -> AnalysisSnapshot:
    snapshot = AnalysisSnapshot(
        instrument_id=instrument.id if instrument else None,
        provider="fixture",
        model="fixture-v1",
        prompt_version=PROMPT_VERSION,
        question="how is it doing?",
        tool_calls=[],
        structured_data_snapshot=[],
        response="looks fine",
        guardrail_flags=[],
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


def test_analyze_without_configured_provider_returns_503(client) -> None:
    response = client.post("/api/v1/ai/analyze", json={"question": "how is BBCA doing?"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_analyze_empty_question_rejected_by_validation(client) -> None:
    response = client.post("/api/v1/ai/analyze", json={"question": ""})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_question_too_long_rejected_by_validation(client) -> None:
    response = client.post("/api/v1/ai/analyze", json={"question": "x" * 5000})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_analyze_question_at_exact_max_length_passes_validation(client) -> None:
    """Boundary: exactly MAX_QUESTION_LENGTH must pass validation (still
    hits the 503 no-provider-configured path, proving it got past the
    length check rather than being rejected as too long)."""
    response = client.post("/api/v1/ai/analyze", json={"question": "x" * 4000})
    assert response.status_code == 503


def test_analyze_question_one_over_max_length_rejected(client) -> None:
    response = client.post("/api/v1/ai/analyze", json={"question": "x" * 4001})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_snapshots_empty(client) -> None:
    response = client.get("/api/v1/ai/snapshots")
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_list_snapshots_returns_seeded_row(client, db_session) -> None:
    _seed_snapshot(db_session)
    response = client.get("/api/v1/ai/snapshots")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["response"] == "looks fine"


def test_list_snapshots_filters_by_symbol(client, db_session) -> None:
    instrument = _seed_instrument(db_session)
    _seed_snapshot(db_session, instrument)

    response = client.get("/api/v1/ai/snapshots", params={"symbol": "BBCA"})
    assert response.json()["total"] == 1

    response = client.get("/api/v1/ai/snapshots", params={"symbol": "NONE"})
    assert response.json()["total"] == 0


def test_list_snapshots_pagination(client, db_session) -> None:
    for _ in range(3):
        _seed_snapshot(db_session)
    response = client.get("/api/v1/ai/snapshots", params={"page": 1, "page_size": 2})
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2

    response = client.get("/api/v1/ai/snapshots", params={"page": 2, "page_size": 2})
    assert len(response.json()["items"]) == 1


def test_get_snapshot_404_for_unknown_id(client) -> None:
    response = client.get(f"/api/v1/ai/snapshots/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_snapshot_returns_seeded_row(client, db_session) -> None:
    snapshot = _seed_snapshot(db_session)
    response = client.get(f"/api/v1/ai/snapshots/{snapshot.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(snapshot.id)
