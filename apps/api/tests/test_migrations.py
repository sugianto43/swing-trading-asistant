from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _alembic_config(db_url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_upgrade_and_downgrade(tmp_path) -> None:
    db_path = tmp_path / "migrations_test.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "head")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert "users" in inspector.get_table_names()
    engine.dispose()

    command.downgrade(cfg, "base")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert "users" not in inspector.get_table_names()
    engine.dispose()


def test_upgrade_is_idempotent_at_head(tmp_path) -> None:
    db_path = tmp_path / "migrations_idempotent.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # re-running at head must be a safe no-op

    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert inspector.get_table_names().count("users") == 1
    engine.dispose()


def test_downgrade_is_idempotent_at_base(tmp_path) -> None:
    db_path = tmp_path / "migrations_idempotent_down.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    cfg = _alembic_config(db_url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.downgrade(cfg, "base")  # re-running at base must be a safe no-op

    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert "users" not in inspector.get_table_names()
    engine.dispose()
