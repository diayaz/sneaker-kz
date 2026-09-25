import re

from scrapers.base import StoreInfo
from scrapers.shopify import Product, ShopifyScraper, smart_title


class SocialStatusScraper(ShopifyScraper):
    store = StoreInfo(
        code="socialstatus_us",
        name="Social Status",
        country="US",
        currency="USD",
        website="https://www.socialstatuspgh.com",
    )
    domain = "socialstatuspgh.com"

    def color(self, p: Product) -> str | None:
        # «NIKE AIR FORCE 1 "CRACKED LEATHER"» — в кавычках название расцветки
        m = re.search(r'"([^"]+)"', p.get("title") or "")
        return smart_title(m.group(1)) if m else super().color(p)

    def name(self, p: Product) -> str:
        return smart_title((p.get("title") or "").replace('"', "").strip())
