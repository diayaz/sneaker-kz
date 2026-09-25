"""Запуск парсера и сохранение результатов: товары, предложения, размеры, история цен, журнал."""

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Offer, OfferSize, PriceHistory, Product, ScrapeRun, Store
from scrapers.base import BaseScraper, ScrapedProduct, StoreInfo

log = logging.getLogger(__name__)

COMMIT_EVERY = 50
# Если собрано меньше этой доли от прошлого успешного запуска, не помечаем пропавшие товары
# как «нет в наличии»: скорее всего, парсер сломался, а не магазин опустел.
MIN_SHARE_TO_MARK_MISSING = 0.5


def ensure_store(session: Session, info: StoreInfo) -> Store:
    store = session.scalar(select(Store).where(Store.code == info.code))
    if store is None:
        store = Store(code=info.code, default_sales_tax_pct=info.default_sales_tax_pct)
        session.add(store)
    # Налог по умолчанию правят вручную в БД, поэтому его не перезаписываем.
    store.name, store.country = info.name, info.country
    store.currency, store.website = info.currency, info.website
    session.flush()
    return store


def _size_sort_key(size: str) -> float:
    try:
        return float(size)
    except ValueError:
        return 0.0


def save_item(session: Session, store: Store, item: ScrapedProduct, now: datetime, today: date) -> Offer:
    product = session.scalar(select(Product).where(Product.style_code == item.style_code))
    if product is None:
        product = Product(
            style_code=item.style_code,
            brand=item.brand,
            model=item.model,
            name=item.name,
            color=item.color,
            gender=item.gender,
            image_url=item.image_url,
        )
        session.add(product)
        session.flush()
    else:
        # Товар мог прийти из другого магазина — дополняем только пустые поля.
        for attr in ("model", "color", "gender", "image_url"):
            if getattr(product, attr) is None and getattr(item, attr) is not None:
                setattr(product, attr, getattr(item, attr))

    offer = session.scalar(select(Offer).where(Offer.product_id == product.id, Offer.store_id == store.id))
    if offer is None:
        offer = Offer(product_id=product.id, store_id=store.id)
        session.add(offer)
    offer.price, offer.old_price, offer.currency = item.price, item.old_price, item.currency
    offer.in_stock, offer.url = bool(item.in_stock), item.url
    offer.store_product_id = item.store_product_id
    offer.last_seen_at = now

    scraped: dict[tuple[str, str], bool] = {}
    for s in item.sizes:  # дубликат в выдаче магазина — «в наличии» побеждает
        scraped[(s.size, s.width)] = scraped.get((s.size, s.width), False) or s.available
    # Обновляем строки на месте: при полной замене списка INSERT идёт раньше DELETE
    # и упирается в уникальный ключ (offer_id, size, width).
    existing = {(z.size, z.width): z for z in offer.sizes}
    for key, row in existing.items():
        if key in scraped:
            row.available = scraped[key]
        else:
            offer.sizes.remove(row)
    for (size, width), available in scraped.items():
        if (size, width) not in existing:
            offer.sizes.append(OfferSize(size=size, width=width, available=available, sort_key=_size_sort_key(size)))
    session.flush()

    point = session.scalar(select(PriceHistory).where(PriceHistory.offer_id == offer.id, PriceHistory.day == today))
    if point is None:
        session.add(PriceHistory(offer_id=offer.id, day=today, price=item.price, old_price=item.old_price, in_stock=offer.in_stock))
    else:
        point.price, point.old_price, point.in_stock = item.price, item.old_price, offer.in_stock
    return offer


def _mark_missing_out_of_stock(session: Session, store: Store, run: ScrapeRun, started: datetime) -> int:
    prev = session.scalar(
        select(ScrapeRun)
        .where(ScrapeRun.store_id == store.id, ScrapeRun.status == "ok", ScrapeRun.id != run.id)
        .order_by(ScrapeRun.id.desc())
        .limit(1)
    )
    if prev and run.items_ok < prev.items_ok * MIN_SHARE_TO_MARK_MISSING:
        log.warning(
            "[%s] собрано %s против %s в прошлый раз — пропавшие товары не трогаем",
            store.code, run.items_ok, prev.items_ok,
        )
        return 0
    missing = session.scalars(
        select(Offer).where(Offer.store_id == store.id, Offer.in_stock.is_(True), Offer.last_seen_at < started)
    ).all()
    for offer in missing:
        offer.in_stock = False
    return len(missing)


def run_scraper(scraper_cls: type[BaseScraper], session_factory: Callable[[], Session]) -> ScrapeRun:
    started = datetime.now(UTC)
    today = date.today()
    with session_factory() as session:
        store = ensure_store(session, scraper_cls.store)
        run = ScrapeRun(store_id=store.id, started_at=started)
        session.add(run)
        session.commit()
        log.info("[%s] старт", store.code)

        scraper = scraper_cls()
        try:
            for item in scraper.iter_products():
                try:
                    with session.begin_nested():
                        save_item(session, store, item, datetime.now(UTC), today)
                    run.items_ok += 1
                except Exception:
                    run.items_failed += 1
                    log.exception("[%s] не удалось сохранить %s", store.code, getattr(item, "style_code", "?"))
                if (run.items_ok + run.items_failed) % COMMIT_EVERY == 0:
                    session.commit()
                    log.info("[%s] сохранено %s, ошибок %s", store.code, run.items_ok, run.items_failed)
        except Exception as exc:
            # Ошибки сохранения ловятся выше, так что сюда попадают только сбои самого парсера;
            # уже собранные товары сохраняем.
            run.status, run.error = "failed", f"{type(exc).__name__}: {exc}"
            log.exception("[%s] парсер упал", store.code)
        else:
            run.marked_out_of_stock = _mark_missing_out_of_stock(session, store, run, started)
            run.status = "ok" if run.items_failed == 0 else "partial"
        finally:
            scraper.close()

        run.finished_at = datetime.now(UTC)
        session.commit()
        log.info(
            "[%s] итог: %s, собрано %s, ошибок %s, снято с наличия %s",
            store.code, run.status, run.items_ok, run.items_failed, run.marked_out_of_stock,
        )
        return run
