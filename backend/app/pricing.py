"""Калькулятор ориентировочной цены «до двери» в Казахстане.

Итог = (цена + налог штата + доставка посредника) × курс USD + пошлина × курс EUR.
Пошлина по правилам ЕАЭС для личных посылок: 15% с превышения €200 по стоимости,
но не меньше €2 за каждый кг сверх 31 кг. Все параметры — в таблице settings.
"""

from dataclasses import asdict, dataclass, fields
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models import Setting

CENT = Decimal("0.01")
TENGE = Decimal("1")


@dataclass(frozen=True)
class CalcSettings:
    usd_kzt_rate: Decimal
    eur_kzt_rate: Decimal
    rates_date: str
    shipping_usd_per_kg: Decimal
    shoe_weight_kg: Decimal
    duty_free_limit_eur: Decimal
    duty_rate_pct: Decimal
    duty_free_weight_kg: Decimal
    duty_min_eur_per_kg: Decimal
    duty_include_shipping: bool

    @classmethod
    def load(cls, session: Session) -> "CalcSettings":
        raw = {s.key: s.value for s in session.query(Setting)}
        kwargs = {}
        for f in fields(cls):
            value = raw.get(f.name, "")
            if f.type is bool:
                kwargs[f.name] = value.strip() == "1"
            elif f.type is str:
                kwargs[f.name] = value
            else:
                kwargs[f.name] = Decimal(value or "0")
        return cls(**kwargs)


@dataclass(frozen=True)
class PriceBreakdown:
    price_usd: Decimal
    sales_tax_usd: Decimal
    shipping_usd: Decimal
    customs_value_eur: Decimal
    duty_eur: Decimal
    price_kzt: Decimal
    sales_tax_kzt: Decimal
    shipping_kzt: Decimal
    duty_kzt: Decimal
    total_kzt: Decimal

    def as_dict(self) -> dict:
        return asdict(self)


def to_kzt(amount: Decimal, rate: Decimal) -> Decimal:
    return (amount * rate).quantize(TENGE, ROUND_HALF_UP)


def calculate(price_usd: Decimal, sales_tax_pct: Decimal, s: CalcSettings) -> PriceBreakdown:
    tax_usd = (price_usd * sales_tax_pct / 100).quantize(CENT, ROUND_HALF_UP)
    shipping_usd = (s.shipping_usd_per_kg * s.shoe_weight_kg).quantize(CENT, ROUND_HALF_UP)

    customs_usd = price_usd + tax_usd + (shipping_usd if s.duty_include_shipping else 0)
    customs_eur = (customs_usd * s.usd_kzt_rate / s.eur_kzt_rate).quantize(CENT, ROUND_HALF_UP)
    by_value = max(Decimal(0), customs_eur - s.duty_free_limit_eur) * s.duty_rate_pct / 100
    by_weight = max(Decimal(0), s.shoe_weight_kg - s.duty_free_weight_kg) * s.duty_min_eur_per_kg
    duty_eur = max(by_value, by_weight).quantize(CENT, ROUND_HALF_UP)

    parts = {
        "price_kzt": to_kzt(price_usd, s.usd_kzt_rate),
        "sales_tax_kzt": to_kzt(tax_usd, s.usd_kzt_rate),
        "shipping_kzt": to_kzt(shipping_usd, s.usd_kzt_rate),
        "duty_kzt": to_kzt(duty_eur, s.eur_kzt_rate),
    }
    return PriceBreakdown(
        price_usd=price_usd,
        sales_tax_usd=tax_usd,
        shipping_usd=shipping_usd,
        customs_value_eur=customs_eur,
        duty_eur=duty_eur,
        total_kzt=sum(parts.values(), Decimal(0)),
        **parts,
    )
