"""Миграции не должны терять данные — особенно в SQLite, где batch-режим пересоздаёт таблицы."""

from datetime import UTC, date, datetime

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import BACKEND_DIR
from app.db import make_engine
from app.models import Offer, OfferSize, PriceHistory
from scrapers.base import StoreInfo
from scrapers.pipeline import ensure_store, save_item
from tests.test_api import item


def run(engine, *args):
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        getattr(command, args[0])(cfg, *args[1:])


def test_downgrade_and_upgrade_keep_offers(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    run(engine, "upgrade", "head")
    with Session(engine) as s:
        store = ensure_store(s, StoreInfo("a", "A", "US", "USD", "https://a"))
        save_item(s, store, item("DD1391-100", "100", sizes=(("9", True), ("10", True))), datetime.now(UTC), date.today())
        s.commit()

    # Откат и повтор последних миграций пересоздают таблицу products.
    run(engine, "downgrade", "-2")
    run(engine, "upgrade", "head")

    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Offer)) == 1
        assert s.scalar(select(func.count()).select_from(OfferSize)) == 2
        assert s.scalar(select(func.count()).select_from(PriceHistory)) == 1
        assert s.execute(text("PRAGMA foreign_keys")).scalar() == 1  # после миграций ключи снова включены
