from pathlib import Path

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import config

# Явные имена ограничений нужны Alembic, чтобы миграции одинаково работали в SQLite и PostgreSQL.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def make_engine(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url)
    if parsed.get_backend_name() == "sqlite":
        # На каждой выдаче из пула, а не только при создании: миграции временно выключают ключи
        # на своём соединении, и оно не должно вернуться в работу без них.
        event.listen(engine, "checkout", _sqlite_enable_fk)
    return engine


def _sqlite_enable_fk(dbapi_conn, _record, _proxy=None):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


engine = make_engine(config.database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
