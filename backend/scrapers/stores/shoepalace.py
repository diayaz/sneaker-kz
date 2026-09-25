import re

from scrapers.base import StoreInfo
from scrapers.shopify import Product, ShopifyScraper


class ShoePalaceScraper(ShopifyScraper):
    store = StoreInfo(
        code="shoepalace_us",
        name="Shoe Palace",
        country="US",
        currency="USD",
        website="https://www.shoepalace.com",
    )
    domain = "shoepalace.com"

    # Shoe Palace кладёт в SKU свой внутренний номер, а артикул и пол — в теги:
    # STYLE_IR0088-001, Department_Men, Category_Footwear, Product_Shoes.

    def _tag_value(self, p: Product, prefix: str) -> str | None:
        for t in p.get("tags") or []:
            if t.startswith(prefix):
                return t[len(prefix):].strip()
        return None

    def is_sneaker(self, p: Product) -> bool:
        tags = set(p.get("tags") or [])
        return "Category_Footwear" in tags and "Product_Shoes" in tags

    def gender(self, p: Product) -> str | None:
        dept = (self._tag_value(p, "Department_") or "").lower()
        return {"men": "men", "women": "women", "kids": "kids"}.get(dept) or super().gender(p)

    def style_code(self, p: Product) -> str | None:
        return self._tag_value(p, "STYLE_") or self._tag_value(p, "SKU_")

    def _title(self, p: Product) -> str:
        # Приписки после цвета: «(Black/White) Final Sale»
        return re.sub(r"\s+(Final Sale|Limit \d+.*)$", "", p.get("title") or "", flags=re.I).strip()

    def color(self, p: Product) -> str | None:
        # «... Mens Lifestyle Shoes (Black/Varsity Red/Summit White)»
        m = re.search(r"\(([^()]+)\)\s*$", self._title(p))
        return m.group(1).strip() if m else None

    def name(self, p: Product) -> str:
        title = re.sub(r"\s*\([^()]+\)\s*$", "", self._title(p))
        # убираем хвост «Mens Lifestyle Shoes» / «Womens Running Shoes»
        return re.sub(r"\s+(Mens|Womens|Unisex)\s+.*Shoes$", "", title).strip()
