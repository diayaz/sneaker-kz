"""Общий парсер для магазинов на Shopify: публичный каталог /products.json.

Магазин-наследник задаёт `store` и `domain` и при необходимости переопределяет
хуки is_sneaker / gender / style_code / color под то, как магазин размечает товары.
"""

import logging
import re
from collections.abc import Iterator
from decimal import Decimal
from itertools import count
from typing import Any, ClassVar

from scrapers.base import BaseScraper, ScrapedProduct, ScrapedSize
from scrapers.http import PoliteClient

log = logging.getLogger(__name__)

Product = dict[str, Any]

KIDS_RE = re.compile(
    r"\b(GS|PS|TD|kids?|grade ?school|pre-?school|toddlers?|infants?|little kids|big kids|youth|crib)\b"
    r"|\(\s*(GS|PS|TD|C|Y)\s*\)",
    re.I,
)
KIDS_SIZE_RE = re.compile(r"^\d+(\.5)?\s*[CY]$", re.I)  # «10.5C», «5Y»
WOMEN_RE = re.compile(r"\b(women'?s?|wmns|womens)\b|\(W\)", re.I)
MEN_RE = re.compile(r"\b(men'?s?|mens)\b", re.I)

BRAND_ALIASES = {
    "NIKE": "Nike",
    "JORDAN": "Jordan",
    "AIR JORDAN": "Jordan",
    "JORDAN BRAND": "Jordan",
    "ADIDAS": "Adidas",
    "ADIDAS ORIGINALS": "Adidas",
    "NEW BALANCE": "New Balance",
    "NEWBALANCE": "New Balance",
    "OFF WHITE": "Off-White",
    "OFF WHITE FTW": "Off-White",
    "OFF-WHITE": "Off-White",
    "DC SHOES": "DC Shoes",
    "UGG": "UGG",
    "PF FLYERS": "PF Flyers",
    "ASICS": "ASICS",
    "HOKA": "HOKA",
    "HOKA ONE ONE": "HOKA",
    "PUMA": "Puma",
    "REEBOK": "Reebok",
    "SAUCONY": "Saucony",
    "CONVERSE": "Converse",
    "VANS": "Vans",
    "ON": "On",
    "ON RUNNING": "On",
    "SALOMON": "Salomon",
}


# Аббревиатуры, которые в названиях кроссовок пишутся заглавными.
KEEP_UPPER = {
    "OG", "SE", "SP", "QS", "PRM", "GTX", "NRG", "SB", "LX", "TR", "DX", "PE", "GS", "PS", "TD",
    "CDG", "BAPE", "OW", "USA", "UK", "II", "III", "IV", "V2", "V3", "WMNS", "EQT", "NMD", "ADV", "FC",
}


def smart_title(text: str) -> str:
    """«AIR JORDAN 1 LOW OG» → «Air Jordan 1 Low OG». Слова с цифрами («1906R», «AF1») не трогаем."""

    def fix(word: str) -> str:
        core = word.strip("\"'()[]/-.,")
        if core.upper() in KEEP_UPPER or any(ch.isdigit() for ch in core):
            return word.upper() if core.upper() in KEEP_UPPER else word
        return word.capitalize() if word.isupper() or word.islower() else word

    return re.sub(r"\S+", lambda m: "/".join(fix(w) for w in m.group(0).split("/")), text)


def normalize_brand(vendor: str) -> str:
    v = re.sub(r"\s+", " ", vendor).strip()
    return BRAND_ALIASES.get(v.upper(), v.title() if v.isupper() else v)


def find_option_index(product: Product, *names: str) -> int | None:
    """Номер опции (0..2) с указанным именем, например Size или Color."""
    for i, opt in enumerate(product.get("options") or []):
        if opt["name"].strip().lower() in names:
            return i
    return None


def to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    d = Decimal(str(value))
    return d if d > 0 else None


class ShopifyScraper(BaseScraper, register=False):
    domain: ClassVar[str]
    page_size: ClassVar[int] = 250
    max_pages: ClassVar[int] = 200  # предохранитель от бесконечной пагинации

    def __init__(self) -> None:
        self.http = PoliteClient()
        self.parse_errors = 0
        self.skipped: dict[str, int] = {}

    def close(self) -> None:
        self.http.close()
        if self.skipped:
            log.info("[%s] пропущено: %s", self.store.code, self.skipped)

    # --- обход каталога -------------------------------------------------

    def iter_raw(self) -> Iterator[Product]:
        for page in count(1):
            if page > self.max_pages:
                log.warning("[%s] достигнут лимит в %s страниц", self.store.code, self.max_pages)
                return
            data = self.http.get_json(
                f"https://{self.domain}/products.json",
                # currency=USD — иначе Shopify пересчитывает цены в валюту страны посетителя
                params={"limit": self.page_size, "page": page, "currency": "USD"},
            )
            products = data.get("products") or []
            if not products:
                return
            log.info("[%s] страница %s: %s товаров", self.store.code, page, len(products))
            yield from products

    def iter_products(self) -> Iterator[ScrapedProduct]:
        for raw in self.iter_raw():
            try:
                item = self.parse(raw)
            except Exception:
                self.parse_errors += 1
                log.exception("[%s] не удалось разобрать %s", self.store.code, raw.get("handle"))
                continue
            if item is not None:
                yield item

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    # --- разбор товара --------------------------------------------------

    def parse(self, p: Product) -> ScrapedProduct | None:
        if not self.is_sneaker(p):
            self._skip("не кроссовки")
            return None
        size_idx = find_option_index(p, "size", "us size", "shoe size")
        if size_idx is None:
            self._skip("нет размеров")
            return None
        variants = p.get("variants") or []
        sizes = [
            ScrapedSize(size=str(v.get(f"option{size_idx + 1}") or "").strip(), available=bool(v.get("available")))
            for v in variants
        ]
        gender = self.gender(p)
        if gender == "kids" or any(KIDS_SIZE_RE.match(s.size) for s in sizes):
            self._skip("детские")
            return None
        code = self.style_code(p)
        if not code:
            self._skip("нет артикула")
            return None

        # Цена — минимальная среди размеров в наличии (если в наличии ничего, то среди всех).
        priced = [v for v in variants if to_decimal(v.get("price"))]
        in_stock = [v for v in priced if v.get("available")] or priced
        if not in_stock:
            self._skip("нет цены")
            return None
        best = min(in_stock, key=lambda v: to_decimal(v["price"]))

        return ScrapedProduct(
            style_code=code,
            brand=normalize_brand(p.get("vendor") or ""),
            name=self.name(p),
            price=to_decimal(best["price"]),
            old_price=to_decimal(best.get("compare_at_price")),
            color=self.color(p),
            gender=gender,
            image_url=(p.get("images") or [{}])[0].get("src"),
            url=f"https://{self.domain}/products/{p['handle']}",
            sizes=[s for s in sizes if s.size],
            store_product_id=str(p["id"]),
        )

    # --- хуки для конкретных магазинов --------------------------------------

    def is_sneaker(self, p: Product) -> bool:
        ptype = (p.get("product_type") or "").strip().lower()
        tags = {t.lower() for t in p.get("tags") or []}
        return ptype in {"sneakers", "footwear", "shoes"} or "sneakers" in tags

    def gender(self, p: Product) -> str | None:
        """'men' / 'women' / 'kids' / None (не определён или унисекс)."""
        tags = {t.lower() for t in p.get("tags") or []}
        title = p.get("title") or ""
        if tags & {"kids", "youth", "grade school", "preschool", "toddler"} or KIDS_RE.search(title):
            return "kids"
        if tags & {"womens", "women", "wmns"} or WOMEN_RE.search(title):
            return "women"
        if tags & {"mens", "men"} or MEN_RE.search(title):
            return "men"
        return None

    def style_code(self, p: Product) -> str | None:
        for v in p.get("variants") or []:
            sku = (v.get("sku") or "").split("|")[0].strip()
            if sku:
                return sku
        return None

    def color(self, p: Product) -> str | None:
        idx = find_option_index(p, "color", "colour")
        if idx is not None:
            values = p["options"][idx].get("values") or []
            if values:
                return smart_title(str(values[0]).strip())
        return None

    def name(self, p: Product) -> str:
        return re.sub(r"\s+", " ", p.get("title") or "").strip()
