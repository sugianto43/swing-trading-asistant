import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.db.session import build_engine


def test_engine_connects() -> None:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    assert result == 1


def test_engine_uses_settings_url_when_none_given() -> None:
    engine = build_engine()
    assert str(engine.url) == get_settings().database_url


def test_unreachable_database_raises_not_silently_swallowed() -> None:
    # Nonexistent sqlite path under a nonexistent directory forces a real
    # connection failure so we can assert the error propagates instead of
    # being swallowed (rule: never silently swallow errors).
    engine = build_engine("sqlite+pysqlite:////nonexistent-dir/does-not-exist.db")
    with pytest.raises(OperationalError):
        engine.connect()
