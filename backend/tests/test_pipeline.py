from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import Base, make_engine
from app.models import Offer, PriceHistory, Product, ScrapeRun
from scrapers import pipeline
from scrapers.base import BaseScraper, ScrapedProduct, ScrapedSize, StoreInfo, get_registry


def make_item(code: str, price: str, old: str | None = None, sizes=(("9", True), ("10", False))) -> ScrapedProduct:
    return ScrapedProduct(
        style_code=code,
        brand="New Balance",
        name=f"Shoe {code}",
        price=Decimal(price),
        old_price=Decimal(old) if old else None,
        url=f"https://example.com/{code}",
        sizes=[ScrapedSize(s, a) for s, a in sizes],
    )


def fake_scraper(code: str, items: list[ScrapedProduct], fail: bool = False) -> type[BaseScraper]:
    class Fake(BaseScraper, register=False):
        store = StoreInfo(code=code, name=code, country="US", currency="USD", website="https://example.com")

        def iter_products(self):
            yield from items
            if fail:
                raise RuntimeError("boom")

    return Fake


@pytest.fixture
def session_factory():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def test_saves_products_offers_and_history(session_factory):
    run = pipeline.run_scraper(fake_scraper("nb", [make_item("m990-gl6", "199.99", "219.99")]), session_factory)
    assert (run.status, run.items_ok) == ("ok", 1)

    with session_factory() as s:
        product = s.scalar(select(Product))
        assert product.style_code == "M990GL6"
        offer = product.offers[0]
        assert offer.price == Decimal("199.99") and offer.old_price == Decimal("219.99")
        assert [(z.size, z.available) for z in offer.sizes] == [("9", True), ("10", False)]
        assert offer.in_stock is True
        assert len(offer.history) == 1


def test_same_style_code_from_two_stores_is_one_product(session_factory):
    pipeline.run_scraper(fake_scraper("a", [make_item("M990GL6", "199.99")]), session_factory)
    pipeline.run_scraper(fake_scraper("b", [make_item("m990gl6", "189.00")]), session_factory)
    with session_factory() as s:
        assert s.query(Product).count() == 1
        assert s.query(Offer).count() == 2


def test_rerun_same_day_updates_history_point(session_factory):
    pipeline.run_scraper(fake_scraper("nb", [make_item("X1", "100")]), session_factory)
    pipeline.run_scraper(fake_scraper("nb", [make_item("X1", "90")]), session_factory)
    with session_factory() as s:
        points = s.scalars(select(PriceHistory)).all()
        assert [p.price for p in points] == [Decimal("90")]


def test_missing_items_marked_out_of_stock(session_factory):
    pipeline.run_scraper(fake_scraper("nb", [make_item("X1", "100"), make_item("X2", "100")]), session_factory)
    run = pipeline.run_scraper(fake_scraper("nb", [make_item("X1", "100")]), session_factory)
    assert run.marked_out_of_stock == 1
    with session_factory() as s:
        x2 = s.scalar(select(Offer).join(Product).where(Product.style_code == "X2"))
        assert x2.in_stock is False


def test_suspiciously_small_run_does_not_mark_missing(session_factory):
    items = [make_item(f"X{i}", "100") for i in range(10)]
    pipeline.run_scraper(fake_scraper("nb", items), session_factory)
    run = pipeline.run_scraper(fake_scraper("nb", items[:2]), session_factory)
    assert run.marked_out_of_stock == 0


def test_scraper_crash_keeps_collected_items(session_factory):
    run = pipeline.run_scraper(fake_scraper("nb", [make_item("X1", "100")], fail=True), session_factory)
    assert run.status == "failed" and "boom" in run.error
    with session_factory() as s:
        assert s.query(Offer).count() == 1
        assert s.scalar(select(ScrapeRun)).marked_out_of_stock == 0


def test_old_price_not_above_price_is_dropped():
    assert make_item("X", "100", "100").old_price is None


def test_fake_scrapers_not_registered():
    fake_scraper("should_not_register", [])
    assert "should_not_register" not in get_registry()
