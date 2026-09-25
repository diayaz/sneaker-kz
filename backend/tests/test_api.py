from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import get_session
from app.db import Base
from app.main import app
from app.models import PriceHistory, Setting
from app.seed import seed_settings
from scrapers.base import ScrapedProduct, ScrapedSize, StoreInfo
from scrapers.pipeline import ensure_store, save_item


def item(code, price, old=None, sizes=(("9", True),), brand="Nike", name=None, gender="men"):
    return ScrapedProduct(
        style_code=code, brand=brand, name=name or f"Shoe {code}", price=Decimal(price),
        old_price=Decimal(old) if old else None, url=f"https://shop/{code}", gender=gender,
        sizes=[ScrapedSize(s, a) for s, a in sizes],
    )


@pytest.fixture
def client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)
    with Session() as s:
        seed_settings(s)
        s.get(Setting, "usd_kzt_rate").value = "450"
        s.get(Setting, "eur_kzt_rate").value = "500"
        a = ensure_store(s, StoreInfo("a", "Store A", "US", "USD", "https://a"))
        b = ensure_store(s, StoreInfo("b", "Store B", "US", "USD", "https://b"))
        now, today = datetime.now(UTC), date.today()
        save_item(s, a, item("DD1391-100", "120", sizes=(("9", True), ("10", False)), name="Dunk Low Panda"), now, today)
        offer = save_item(s, b, item("dd1391 100", "100", "130", sizes=(("10", True),)), now, today)
        s.add(PriceHistory(offer_id=offer.id, day=today - timedelta(days=3), price=Decimal("130"), in_stock=True))
        save_item(s, a, item("GW2871", "90", brand="Adidas", name="Samba OG", gender="women"), now, today)
        sold_out = save_item(s, b, item("OUT-1", "50", sizes=(("9", False),)), now, today)
        assert not sold_out.in_stock
        s.commit()

    def override():
        with Session() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_hides_out_of_stock_and_picks_cheapest_store(client):
    r = client.get("/api/v1/products").json()
    assert r["total"] == 2
    dunk = next(p for p in r["items"] if p["style_code"] == "DD1391-100")
    assert (dunk["best_price"], dunk["best_old_price"], dunk["discount_pct"]) == (100.0, 130.0, 23)
    assert dunk["best_store"]["code"] == "b" and dunk["offers_count"] == 2
    assert dunk["total_kzt"] == (100 + 18) * 450  # цена + доставка 1.5 кг × 12$, без пошлины
    assert r["items"][0]["style_code"] == "DD1391-100"  # popular: больше магазинов — выше


def test_size_filter_uses_available_sizes_only(client):
    r = client.get("/api/v1/products", params={"size": "9"}).json()
    dunk = next(p for p in r["items"] if p["style_code"] == "DD1391-100")
    assert dunk["best_store"]["code"] == "a" and dunk["best_price"] == 120.0  # у B есть только 10-й


def test_search_by_name_and_by_style_code(client):
    assert [p["name"] for p in client.get("/api/v1/products", params={"q": "samba"}).json()["items"]] == ["Samba OG"]
    assert client.get("/api/v1/products", params={"q": "dd1391100"}).json()["total"] == 1


def test_filters_brand_gender_sale_price(client):
    get = lambda **p: {i["style_code"] for i in client.get("/api/v1/products", params=p).json()["items"]}
    assert get(brand="Adidas") == {"GW2871"}
    assert get(gender="women") == {"GW2871"}
    assert get(on_sale=True) == {"DD1391-100"}
    assert get(max_price=95) == {"GW2871"}
    assert get(in_stock=False) == {"DD1391-100", "GW2871", "OUT-1"}


def test_sort_by_price(client):
    items = client.get("/api/v1/products", params={"sort": "price_asc"}).json()["items"]
    assert [i["best_price"] for i in items] == [90.0, 100.0]


def test_product_detail_offers_sorted_with_estimate(client):
    pid = client.get("/api/v1/products", params={"q": "dunk"}).json()["items"][0]["id"]
    d = client.get(f"/api/v1/products/{pid}").json()
    assert [o["store"]["code"] for o in d["offers"]] == ["b", "a"]
    assert d["offers"][1]["sizes"] == [
        {"size": "9", "width": "", "available": True},
        {"size": "10", "width": "", "available": False},
    ]
    assert d["offers"][0]["estimate"]["shipping_usd"] == 18.0


def test_history(client):
    pid = client.get("/api/v1/products", params={"q": "dunk"}).json()["items"][0]["id"]
    h = client.get(f"/api/v1/products/{pid}/history").json()
    by_store = {s["store"]["code"]: [p["price"] for p in s["points"]] for s in h["series"]}
    assert by_store == {"a": [120.0], "b": [130.0, 100.0]}


def test_filters_and_info_endpoints(client):
    f = client.get("/api/v1/filters").json()
    assert {b["name"] for b in f["brands"]} == {"Nike", "Adidas"}
    assert f["sizes"] == ["9", "10"]
    info = client.get("/api/v1/estimate-info").json()
    assert info["usd_kzt_rate"] == 450.0 and "ориентировочная" in info["disclaimer"]


def test_404(client):
    assert client.get("/api/v1/products/999").status_code == 404
    assert client.get("/api/v1/products/999/history").status_code == 404
