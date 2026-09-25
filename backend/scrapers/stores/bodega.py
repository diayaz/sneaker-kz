from scrapers.base import StoreInfo
from scrapers.shopify import Product, ShopifyScraper, smart_title


class BodegaScraper(ShopifyScraper):
    store = StoreInfo(
        code="bodega_us",
        name="Bodega",
        country="US",
        currency="USD",
        website="https://bdgastore.com",
    )
    domain = "bdgastore.com"

    def is_sneaker(self, p: Product) -> bool:
        # В «Footwear» у Bodega есть и тапочки, и сандалии — кроссовки помечены тегом sneakers.
        return "sneakers" in {t.lower() for t in p.get("tags") or []}

    def name(self, p: Product) -> str:
        return smart_title((p.get("title") or "").replace('"', "").strip())
