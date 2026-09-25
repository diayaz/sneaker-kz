"""Командная строка проекта.

    python manage.py init-db            # миграции + настройки по умолчанию
    python manage.py scrapers           # список подключённых магазинов
    python manage.py scrape [код ...]   # запустить парсеры (все или указанные)
    python manage.py rates              # обновить курсы USD/EUR с сайта Нацбанка РК
    python manage.py daily              # ежедневная задача: курсы + все парсеры
    python manage.py stats              # что лежит в базе
"""

import argparse
import sys

from sqlalchemy import func, select

from app.db import SessionLocal
from app.logging_setup import setup_logging
from app.models import Offer, OfferSize, PriceHistory, Product, ScrapeRun, Setting, Store


def cmd_init_db(_args) -> None:
    from alembic import command
    from alembic.config import Config as AlembicConfig

    from app.config import BACKEND_DIR
    from app.seed import seed_settings

    command.upgrade(AlembicConfig(str(BACKEND_DIR / "alembic.ini")), "head")
    with SessionLocal() as session:
        print(f"Миграции применены, добавлено настроек: {seed_settings(session)}")


def cmd_scrapers(_args) -> None:
    from scrapers.base import get_registry

    registry = get_registry()
    if not registry:
        print("Парсеров пока нет (scrapers/stores/*.py)")
    for code, cls in registry.items():
        print(f"{code:20} {cls.store.name} ({cls.store.country}, {cls.store.currency})")


def run_scrapers(codes: list[str]) -> bool:
    """Запускает парсеры по очереди; True, если ни один не упал."""
    from scrapers.base import get_registry
    from scrapers.pipeline import run_scraper

    registry = get_registry()
    codes = codes or list(registry)
    unknown = set(codes) - set(registry)
    if unknown:
        sys.exit(f"Неизвестные магазины: {', '.join(sorted(unknown))}. Доступны: {', '.join(registry)}")
    # Падение одного магазина не должно останавливать остальные — run_scraper ловит ошибки сам.
    runs = [run_scraper(registry[code], SessionLocal) for code in codes]
    return not any(r.status == "failed" for r in runs)


def run_rates() -> bool:
    import logging

    from app.rates import update_rates

    try:
        with SessionLocal() as session:
            update_rates(session)
        return True
    except Exception:
        logging.getLogger("rates").exception("Не удалось обновить курсы — остаются прежние")
        return False


def cmd_scrape(args) -> None:
    setup_logging("scrape")
    if not run_scrapers(args.stores):
        sys.exit(1)


def cmd_rates(_args) -> None:
    setup_logging("rates")
    if not run_rates():
        sys.exit(1)


def cmd_daily(_args) -> None:
    import logging

    setup_logging("daily")
    log = logging.getLogger("daily")
    log.info("=== ежедневный запуск ===")
    rates_ok = run_rates()
    scrapers_ok = run_scrapers([])
    log.info("=== готово: курсы %s, парсеры %s ===", "ok" if rates_ok else "ОШИБКА", "ok" if scrapers_ok else "ОШИБКА")
    if not (rates_ok and scrapers_ok):
        sys.exit(1)


def cmd_stats(_args) -> None:
    with SessionLocal() as s:
        for model in (Store, Product, Offer, OfferSize, PriceHistory, Setting, ScrapeRun):
            print(f"{model.__tablename__:15} {s.scalar(select(func.count()).select_from(model))}")
        print("\nНастройки:")
        for st in s.scalars(select(Setting).order_by(Setting.key)):
            print(f"  {st.key:22} = {st.value:8}  {st.description}")
        last_runs = s.execute(
            select(Store.code, ScrapeRun).join(ScrapeRun, ScrapeRun.store_id == Store.id).order_by(ScrapeRun.id.desc()).limit(10)
        ).all()
        if last_runs:
            print("\nПоследние запуски:")
            for code, r in last_runs:
                print(f"  {r.started_at:%Y-%m-%d %H:%M} {code:18} {r.status:8} ok={r.items_ok} err={r.items_failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db").set_defaults(func=cmd_init_db)
    sub.add_parser("scrapers").set_defaults(func=cmd_scrapers)
    p = sub.add_parser("scrape")
    p.add_argument("stores", nargs="*")
    p.set_defaults(func=cmd_scrape)
    sub.add_parser("rates").set_defaults(func=cmd_rates)
    sub.add_parser("daily").set_defaults(func=cmd_daily)
    sub.add_parser("stats").set_defaults(func=cmd_stats)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
