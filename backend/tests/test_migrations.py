"""Alembic migrations apply cleanly, match the models, and downgrade."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db.base import Base
from app.db.session import build_engine

BACKEND = Path(__file__).resolve().parents[1]


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logging"] = False
    return cfg


def test_upgrade_matches_models_and_downgrades(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    cfg = _config(url)
    command.upgrade(cfg, "head")

    engine = build_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
        assert diff == []
        assert set(Base.metadata.tables) <= set(inspect(conn).get_table_names())

    command.downgrade(cfg, "base")
    with engine.connect() as conn:
        assert inspect(conn).get_table_names() == ["alembic_version"]
    engine.dispose()
