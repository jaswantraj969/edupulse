from sqlalchemy import text

from app.db import session as session_module


def test_get_db_yields_working_session_and_closes() -> None:
    session_module.get_engine.cache_clear()
    session_module.get_session_factory.cache_clear()
    gen = session_module.get_db()
    db = next(gen)
    assert db.execute(text("select 1")).scalar() == 1
    gen.close()
    assert str(session_module.get_engine().url) == "sqlite://"


def test_build_engine_for_server_database_uses_pre_ping() -> None:
    engine = session_module.build_engine("postgresql+psycopg://u:p@127.0.0.1:1/x")
    assert engine.pool._pre_ping
    engine.dispose()
