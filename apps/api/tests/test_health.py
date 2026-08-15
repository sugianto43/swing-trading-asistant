from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app


def _override_get_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    session_local = sessionmaker(bind=engine)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_ok() -> None:
    response = client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["app_name"] == "idx-swing-api"
    assert "app_env" in body


def test_404_error_envelope_absent_route() -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "HTTP_ERROR", "message": "Not Found", "details": None}
    }


def test_health_returns_safe_error_envelope_when_db_unavailable() -> None:
    def _broken_get_db():
        raise RuntimeError("simulated database outage: connection refused")
        yield  # pragma: no cover - generator shape only

    unsafe_client = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides[get_db] = _broken_get_db
    try:
        response = unsafe_client.get("/api/v1/health")
    finally:
        app.dependency_overrides[get_db] = _override_get_db

    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": None,
        }
    }
    # the raw exception message/details must never leak to the client
    assert "simulated database outage" not in response.text
