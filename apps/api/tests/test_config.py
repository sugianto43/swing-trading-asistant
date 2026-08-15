import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings


def test_settings_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "idx-swing-api"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.cors_allow_origins == ["http://localhost:3000"]


def test_settings_cors_origins_from_env(monkeypatch) -> None:
    monkeypatch.setenv("cors_allow_origins", '["http://localhost:3000", "http://localhost:4000"]')
    settings = Settings(_env_file=None)
    assert settings.cors_allow_origins == ["http://localhost:3000", "http://localhost:4000"]


def test_settings_env_override(monkeypatch) -> None:
    monkeypatch.setenv("app_env", "production")
    settings = Settings(_env_file=None)
    assert settings.app_env == "production"


def test_get_settings_cached() -> None:
    assert get_settings() is get_settings()


def test_settings_rejects_empty_database_url(monkeypatch) -> None:
    monkeypatch.setenv("database_url", "")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_unsupported_database_scheme(monkeypatch) -> None:
    monkeypatch.setenv("database_url", "mongodb://localhost:27017/idx_swing")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_accepts_sqlite_url(monkeypatch) -> None:
    monkeypatch.setenv("database_url", "sqlite+pysqlite:///:memory:")
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite+pysqlite:///:memory:"
