"""Схемы ответов API (общие для сайта и мобильных приложений)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Деньги отдаём числами, а не строками — так удобнее клиентам.
Usd = Annotated[Decimal, PlainSerializer(float, return_type=float)]
Kzt = Annotated[Decimal, PlainSerializer(int, return_type=int)]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StoreOut(Schema):
    code: str
    name: str
    country: str
    website: str


class SizeOut(Schema):
    size: str
    width: str
    available: bool


class PriceBreakdownOut(Schema):
    price_usd: Usd
    sales_tax_usd: Usd
    shipping_usd: Usd
    customs_value_eur: Usd
    duty_eur: Usd
    price_kzt: Kzt
    sales_tax_kzt: Kzt
    shipping_kzt: Kzt
    duty_kzt: Kzt
    total_kzt: Kzt


class OfferOut(Schema):
    id: int
    store: StoreOut
    price: Usd
    old_price: Usd | None
    discount_pct: int | None
    currency: str
    in_stock: bool
    url: str
    sizes: list[SizeOut]
    updated_at: datetime
    estimate: PriceBreakdownOut


class ProductBase(Schema):
    id: int
    style_code: str
    brand: str
    name: str
    color: str | None
    gender: str | None
    image_url: str | None


class ProductCard(ProductBase):
    """Товар в списке: лучшее предложение среди подходящих под фильтр."""

    best_price: Usd
    best_old_price: Usd | None
    discount_pct: int | None
    best_store: StoreOut
    total_kzt: Kzt
    offers_count: int


class ProductList(Schema):
    items: list[ProductCard]
    total: int
    page: int
    page_size: int


class ProductDetail(ProductBase):
    offers: list[OfferOut]  # сначала в наличии, затем по итоговой цене


class PricePoint(Schema):
    day: date
    price: Usd
    old_price: Usd | None
    in_stock: bool


class PriceSeries(Schema):
    store: StoreOut
    points: list[PricePoint]


class PriceHistoryOut(Schema):
    product_id: int
    series: list[PriceSeries]


class BrandCount(Schema):
    name: str
    count: int


class FiltersOut(Schema):
    brands: list[BrandCount]
    sizes: list[str]
    price_min: Usd | None
    price_max: Usd | None


class EstimateInfo(Schema):
    usd_kzt_rate: Usd
    eur_kzt_rate: Usd
    rates_date: str
    shipping_usd_per_kg: Usd
    shoe_weight_kg: Usd
    duty_free_limit_eur: Usd
    duty_rate_pct: Usd
    disclaimer: str
