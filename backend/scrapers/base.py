import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar

_REGISTRY: dict[str, type["BaseScraper"]] = {}


@dataclass(frozen=True)
class StoreInfo:
    code: str
    name: str
    country: str
    currency: str
    website: str
    default_sales_tax_pct: Decimal = Decimal("0")


@dataclass
class ScrapedSize:
    size: str  # US-размер как в магазине
    available: bool
    width: str = ""


@dataclass
class ScrapedProduct:
    style_code: str
    brand: str
    name: str
    price: Decimal
    url: str
    currency: str = "USD"
    old_price: Decimal | None = None
    model: str | None = None
    color: str | None = None
    gender: str | None = None
    image_url: str | None = None
    sizes: list[ScrapedSize] = field(default_factory=list)
    in_stock: bool | None = None  # None — вычислить по размерам
    store_product_id: str | None = None

    def __post_init__(self) -> None:
        self.style_code = clean_style_code(self.style_code)
        if not self.match_key:
            raise ValueError(f"пустой артикул у {self.name!r}")
        if self.in_stock is None:
            self.in_stock = any(s.available for s in self.sizes)
        if self.old_price is not None and self.old_price <= self.price:
            self.old_price = None

    @property
    def match_key(self) -> str:
        return style_match_key(self.style_code)


class BaseScraper(ABC):
    """Общий интерфейс парсера. Подкласс задаёт `store` и реализует `iter_products`.

    Подклассы регистрируются автоматически; для тестовых классов — `class X(BaseScraper, register=False)`.
    """

    store: ClassVar[StoreInfo]

    def __init_subclass__(cls, register: bool = True, **kwargs):
        super().__init_subclass__(**kwargs)
        if register:
            _REGISTRY[cls.store.code] = cls

    @abstractmethod
    def iter_products(self) -> Iterator[ScrapedProduct]:
        """Отдаёт товары по одному. Ошибку в отдельном товаре лучше залогировать и пропустить;
        исключение наружу означает, что весь запуск провален."""

    def close(self) -> None:  # noqa: B027 — переопределяется при необходимости
        pass


def clean_style_code(code: str) -> str:
    """Артикул для показа: как в магазине, только без лишних пробелов и в верхнем регистре."""
    return re.sub(r"\s+", " ", code).strip().upper()


def style_match_key(code: str) -> str:
    """Ключ сопоставления между магазинами: «IQ6573-100», «iq6573 100» → «IQ6573100»."""
    return re.sub(r"[^0-9A-Za-z]", "", code).upper()


def get_registry() -> dict[str, type[BaseScraper]]:
    import importlib
    import pkgutil

    from scrapers import stores

    for mod in pkgutil.iter_modules(stores.__path__):
        importlib.import_module(f"scrapers.stores.{mod.name}")
    return dict(_REGISTRY)
