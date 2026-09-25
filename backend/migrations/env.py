from logging.config import fileConfig

from alembic import context

from app import models  # noqa: F401 — регистрирует таблицы в metadata
from app.db import Base, engine

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url), target_metadata=target_metadata, literal_binds=True, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


def _migrate(connection) -> None:
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        # Batch-режим SQLite пересоздаёт таблицу (copy → DROP → rename). С включёнными внешними
        # ключами DROP каскадно удалил бы все offers/price_history. PRAGMA работает только вне транзакции.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        # render_as_batch — чтобы ALTER TABLE работал и в SQLite
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        if sqlite:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def run_migrations_online() -> None:
    # Тесты передают своё соединение через config.attributes.
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _migrate(connection)
        return
    with engine.connect() as connection:
        _migrate(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
