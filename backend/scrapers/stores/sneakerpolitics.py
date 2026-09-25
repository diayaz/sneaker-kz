import re

from scrapers.base import StoreInfo
from scrapers.shopify import Product, ShopifyScraper


class SneakerPoliticsScraper(ShopifyScraper):
    store = StoreInfo(
        code="sneakerpolitics_us",
        name="Sneaker Politics",
        country="US",
        currency="USD",
        website="https://sneakerpolitics.com",
    )
    domain = "sneakerpolitics.com"

    # SKU: «HQ2592-702|7.5» — базовый хук уже отрезает размер после «|».

    def color(self, p: Product) -> str | None:
        # «Nike Pegasus Premium - Volt Ice/Black Spruce»
        m = re.search(r"\s-\s(.+)$", p.get("title") or "")
        return m.group(1).strip() if m else None

    def name(self, p: Product) -> str:
        return re.sub(r"\s-\s.+$", "", p.get("title") or "").strip()
