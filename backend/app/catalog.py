"""Запросы каталога: список с фильтрами, карточка товара, история цен."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import ColumnElement, and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Offer, OfferSize, PriceHistory, Product, Store
from app.pricing import CalcSettings, calculate

Sort = Literal["popular", "price_asc", "price_desc", "discount", "new"]


@dataclass
class ProductFilter:
    q: str | None = None
    brands: list[str] = field(default_factory=list)
    sizes: list[str] = field(default_factory=list)
    gender: Literal["men", "women"] | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    on_sale: bool = False
    in_stock: bool = True
    stores: list[str] = field(default_factory=list)


def discount_pct(price: Decimal, old: Decimal | None) -> int | None:
    if not old or old <= price:
        return None
    return int((old - price) * 100 / old)


def _offer_conditions(f: ProductFilter) -> list[ColumnElement[bool]]:
    """Условия на предложение: товар попадает в выдачу, если есть хоть одно подходящее."""
    conds: list[ColumnElement[bool]] = []
    if f.in_stock:
        conds.append(Offer.in_stock.is_(True))
    if f.sizes:
        conds.append(
            exists().where(OfferSize.offer_id == Offer.id, OfferSize.size.in_(f.sizes), OfferSize.available.is_(True))
        )
    if f.min_price is not None:
        conds.append(Offer.price >= f.min_price)
    if f.max_price is not None:
        conds.append(Offer.price <= f.max_price)
    if f.on_sale:
        conds.append(Offer.old_price.is_not(None))
    if f.stores:
        conds.append(Offer.store.has(Store.code.in_(f.stores)))
    return conds


def _product_conditions(f: ProductFilter) -> list[ColumnElement[bool]]:
    from scrapers.base import style_match_key

    conds: list[ColumnElement[bool]] = []
    if f.brands:
        conds.append(Product.brand.in_(f.brands))
    if f.gender:
        # Товары без пола считаем унисекс и показываем в обоих разделах.
        conds.append(or_(Product.gender == f.gender, Product.gender.is_(None)))
    for token in (f.q or "").split():
        like = f"%{token}%"
        variants = [Product.name.ilike(like), Product.brand.ilike(like), Product.style_code.ilike(like)]
        if any(ch.isdigit() for ch in token):  # «iq6573 100», «IQ6573100» — поиск по артикулу
            variants.append(Product.match_key.contains(style_match_key(token)))
        conds.append(or_(*variants))
    return conds


def list_products(
    session: Session, f: ProductFilter, calc: CalcSettings, sort: Sort = "popular", page: int = 1, page_size: int = 24
) -> tuple[list[dict], int]:
    offer_conds = _offer_conditions(f)
    disc = func.coalesce((Offer.old_price - Offer.price) / Offer.old_price, 0)
    agg = (
        select(
            Offer.product_id.label("pid"),
            func.min(Offer.price).label("best"),
            func.count().label("n"),
            func.max(disc).label("disc"),
        )
        .where(*offer_conds)
        .group_by(Offer.product_id)
        .subquery()
    )
    stmt = select(Product).join(agg, agg.c.pid == Product.id).where(*_product_conditions(f))
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    order = {
        "popular": (agg.c.n.desc(), agg.c.disc.desc()),  # есть в большем числе магазинов, потом скидка
        "price_asc": (agg.c.best.asc(),),
        "price_desc": (agg.c.best.desc(),),
        "discount": (agg.c.disc.desc(), agg.c.best.asc()),
        "new": (Product.created_at.desc(),),
    }[sort]
    products = session.scalars(stmt.order_by(*order, Product.id).offset((page - 1) * page_size).limit(page_size)).all()
    if not products:
        return [], total

    # Лучшее предложение для каждого товара — среди тех же, что прошли фильтр.
    offers = session.scalars(
        select(Offer)
        .options(selectinload(Offer.store))
        .where(Offer.product_id.in_([p.id for p in products]), *offer_conds)
    ).all()
    by_product: dict[int, list[Offer]] = {}
    for o in offers:
        by_product.setdefault(o.product_id, []).append(o)

    items = []
    for p in products:
        candidates = by_product[p.id]
        best = min(candidates, key=lambda o: (calculate(o.price, o.store.default_sales_tax_pct, calc).total_kzt, o.id))
        items.append(
            {
                **_product_fields(p),
                "best_price": best.price,
                "best_old_price": best.old_price,
                "discount_pct": discount_pct(best.price, best.old_price),
                "best_store": best.store,
                "total_kzt": calculate(best.price, best.store.default_sales_tax_pct, calc).total_kzt,
                "offers_count": len(candidates),
            }
        )
    return items, total


def get_product(session: Session, product_id: int, calc: CalcSettings) -> dict | None:
    product = session.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.offers).selectinload(Offer.store), selectinload(Product.offers).selectinload(Offer.sizes))
    )
    if product is None:
        return None
    offers = []
    for o in product.offers:
        estimate = calculate(o.price, o.store.default_sales_tax_pct, calc)
        offers.append(
            {
                "id": o.id,
                "store": o.store,
                "price": o.price,
                "old_price": o.old_price,
                "discount_pct": discount_pct(o.price, o.old_price),
                "currency": o.currency,
                "in_stock": o.in_stock,
                "url": o.url,
                "sizes": o.sizes,
                "updated_at": o.last_seen_at,
                "estimate": estimate.as_dict(),
            }
        )
    offers.sort(key=lambda o: (not o["in_stock"], o["estimate"]["total_kzt"]))
    return {**_product_fields(product), "offers": offers}


def price_history(session: Session, product_id: int, days: int) -> dict | None:
    if session.get(Product, product_id) is None:
        return None
    since = date.today() - timedelta(days=days)
    rows = session.execute(
        select(PriceHistory, Store)
        .join(Offer, PriceHistory.offer_id == Offer.id)
        .join(Store, Offer.store_id == Store.id)
        .where(Offer.product_id == product_id, PriceHistory.day >= since)
        .order_by(Store.name, PriceHistory.day)
    ).all()
    series: dict[int, dict] = {}
    for point, store in rows:
        series.setdefault(store.id, {"store": store, "points": []})["points"].append(point)
    return {"product_id": product_id, "series": list(series.values())}


def filters(session: Session) -> dict:
    in_stock = and_(Offer.in_stock.is_(True))
    brands = session.execute(
        select(Product.brand, func.count(func.distinct(Product.id)))
        .join(Offer, Offer.product_id == Product.id)
        .where(in_stock)
        .group_by(Product.brand)
        .order_by(func.count(func.distinct(Product.id)).desc())
    ).all()
    sizes = session.execute(
        select(OfferSize.size, func.min(OfferSize.sort_key))
        .join(Offer, OfferSize.offer_id == Offer.id)
        .where(in_stock, OfferSize.available.is_(True))
        .group_by(OfferSize.size)
    ).all()
    lo, hi = session.execute(select(func.min(Offer.price), func.max(Offer.price)).where(in_stock)).one()
    return {
        "brands": [{"name": b, "count": n} for b, n in brands],
        # Числовые размеры по порядку; экзотика вроде «M9 / W10.5» — в конце.
        "sizes": [s for s, k in sorted(sizes, key=lambda r: (r[1] == 0, r[1], r[0]))],
        "price_min": lo,
        "price_max": hi,
    }


def _product_fields(p: Product) -> dict:
    return {
        "id": p.id,
        "style_code": p.style_code,
        "brand": p.brand,
        "name": p.name,
        "color": p.color,
        "gender": p.gender,
        "image_url": p.image_url,
    }
