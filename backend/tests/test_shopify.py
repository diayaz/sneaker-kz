from decimal import Decimal

import pytest

from scrapers.base import get_registry
from scrapers.shopify import normalize_brand, smart_title
from scrapers.stores.bodega import BodegaScraper
from scrapers.stores.shoepalace import ShoePalaceScraper
from scrapers.stores.sneakerpolitics import SneakerPoliticsScraper
from scrapers.stores.socialstatus import SocialStatusScraper


def variant(size, sku, price, available=True, compare=None, color=None):
    v = {"sku": sku, "price": price, "compare_at_price": compare, "available": available}
    if color:
        v.update(option1=color, option2=size)
    else:
        v.update(option1=size)
    return v


def product(title, vendor, ptype, tags, variants, color_option=None):
    options = [{"name": "Size", "values": []}]
    if color_option:
        options.insert(0, {"name": "Color", "values": [color_option]})
    return {
        "id": 123,
        "title": title,
        "handle": "some-handle",
        "vendor": vendor,
        "product_type": ptype,
        "tags": tags,
        "options": options,
        "variants": variants,
        "images": [{"src": "https://cdn.shopify.com/x.jpg"}],
    }


@pytest.fixture(autouse=True)
def no_http(monkeypatch):
    # Разбор не должен ходить в сеть; клиент создаётся в __init__, подменяем его.
    monkeypatch.setattr("scrapers.shopify.PoliteClient", lambda: None)


def test_sneakerpolitics_sale_item():
    p = product(
        "Nike Pegasus Premium - Volt Ice/Black Spruce", "Nike", "Sneakers", ["footwear", "sale"],
        [
            variant("7.5", "HQ2592-702|7.5", "121.00", available=False, compare="220.00"),
            variant("9", "HQ2592-702|9", "121.00", compare="220.00"),
        ],
    )
    item = SneakerPoliticsScraper().parse(p)
    assert item.style_code == "HQ2592-702"
    assert (item.price, item.old_price) == (Decimal("121.00"), Decimal("220.00"))
    assert (item.name, item.color, item.brand) == ("Nike Pegasus Premium", "Volt Ice/Black Spruce", "Nike")
    assert [(s.size, s.available) for s in item.sizes] == [("7.5", False), ("9", True)]
    assert item.in_stock and item.url == "https://sneakerpolitics.com/products/some-handle"


def test_sneakerpolitics_kids_skipped_by_title_and_size():
    s = SneakerPoliticsScraper()
    kids = product("Nike Air Max 95 (PS) - Black/Pink Foam", "Nike", "Sneakers", ["footwear"],
                   [variant("10.5C", "905461-075|10.5C", "112.00")])
    assert s.parse(kids) is None
    assert s.skipped == {"детские": 1}


def test_socialstatus_gender_and_color():
    p = product('NIKE AIR FORCE 1 "CRACKED LEATHER"', "NIKE", "SNEAKERS", ["mens", "sneakers"],
                [variant("9", "JA0248-001", "140.00")])
    item = SocialStatusScraper().parse(p)
    assert (item.style_code, item.gender, item.color, item.brand) == ("JA0248-001", "men", "Cracked Leather", "Nike")
    assert item.old_price is None


def test_bodega_needs_sneakers_tag_and_color_option():
    s = BodegaScraper()
    house_shoe = product("INCREDIBLE HOUSE SHOE", "Shaka Wear", "Footwear", ["casual"],
                         [variant("7", "IHS02", "40.00", color="BLACK")], color_option="BLACK")
    assert s.parse(house_shoe) is None
    aj7 = product('AIR JORDAN 7 RETRO "MIRO"', "Air Jordan", "Footwear", ["sneakers"],
                  [variant("9", "IQ6573-100", "255.00", color="WHITE/GOLD/RED")], color_option="WHITE/GOLD/RED")
    item = s.parse(aj7)
    assert (item.style_code, item.brand, item.color, item.name) == ("IQ6573-100", "Jordan", "White/Gold/Red", "Air Jordan 7 Retro Miro")
    assert [z.size for z in item.sizes] == ["9"]  # размер из option2, а не цвет


def test_shoepalace_style_from_tags():
    tags = ["Category_Footwear", "Product_Shoes", "Department_Men", "STYLE_IR0088-001", "SKU_IR0088-001"]
    p = product("Air Jordan 1 Retro Low OG Garden Mens Lifestyle Shoes (Black/Varsity Red/Summit White)",
                "JORDAN", "TRUE RETRO", tags, [variant("9", "21143831", "155.00", compare="0.00")])
    item = ShoePalaceScraper().parse(p)
    assert item.style_code == "IR0088-001"  # не внутренний SKU 21143831
    assert (item.gender, item.name, item.color) == ("men", "Air Jordan 1 Retro Low OG Garden", "Black/Varsity Red/Summit White")
    assert item.old_price is None  # compare_at_price «0.00» — не скидка


def test_shoepalace_kids_department_skipped():
    tags = ["Category_Footwear", "Product_Shoes", "Department_Kids", "STYLE_X1"]
    p = product("Something Grade School Shoes (Black)", "NIKE", "LIFESTYLE", tags, [variant("5", "1", "90")])
    assert ShoePalaceScraper().parse(p) is None


def test_price_prefers_available_sizes():
    p = product("Shoe - Red", "Nike", "Sneakers", [], [
        variant("8", "A1|8", "80.00", available=False),
        variant("9", "A1|9", "100.00"),
    ])
    assert SneakerPoliticsScraper().parse(p).price == Decimal("100.00")


def test_shoepalace_final_sale_suffix():
    tags = ["Category_Footwear", "Product_Shoes", "Department_Men", "STYLE_HM1234-100"]
    p = product("Air Pegasus Wave Mens Running Shoes (Sundial/University Blue) Final Sale", "NIKE", "RUNNING", tags,
                [variant("9", "1", "59.98", compare="160.00")])
    item = ShoePalaceScraper().parse(p)
    assert (item.name, item.color) == ("Air Pegasus Wave", "Sundial/University Blue")


@pytest.mark.parametrize("raw, expected", [
    ("AIR JORDAN 1 LOW OG", "Air Jordan 1 Low OG"),
    ("NIKE AIR FORCE 1 '07 LX", "Nike Air Force 1 '07 LX"),
    ("NEW BALANCE 1906R", "New Balance 1906R"),
    ("WHITE/GOLD/RED", "White/Gold/Red"),
    ("Samba OG", "Samba OG"),  # смешанный регистр не трогаем
])
def test_smart_title(raw, expected):
    assert smart_title(raw) == expected


def test_brand_aliases():
    assert normalize_brand("JORDAN BRAND") == "Jordan"
    assert normalize_brand("NEW BALANCE") == "New Balance"
    assert normalize_brand("SOME BRAND") == "Some Brand"
    assert normalize_brand("Maison Margiela") == "Maison Margiela"


def test_stores_registered():
    assert {"sneakerpolitics_us", "socialstatus_us", "bodega_us", "shoepalace_us"} <= set(get_registry())
