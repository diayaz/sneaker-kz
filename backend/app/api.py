from collections.abc import Iterator
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import catalog
from app.db import SessionLocal
from app.models import Store
from app.pricing import CalcSettings
from app.schemas import EstimateInfo, FiltersOut, PriceHistoryOut, ProductDetail, ProductList, StoreOut

DISCLAIMER = (
    "Итоговая цена — ориентировочная оценка: курс Нацбанка РК, примерный тариф посредника "
    "и пошлина по правилам ЕАЭС для личных посылок. Точную стоимость уточняйте у магазина и посредника."
)

router = APIRouter(prefix="/api/v1")


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/products", response_model=ProductList, summary="Поиск и каталог")
def list_products(
    session: SessionDep,
    q: str | None = Query(None, description="Название, бренд или артикул"),
    brand: list[str] = Query([], description="Можно несколько: ?brand=Nike&brand=Adidas"),
    size: list[str] = Query([], description="US-размеры в наличии: ?size=9&size=9.5"),
    gender: Literal["men", "women"] | None = None,
    min_price: Decimal | None = Query(None, ge=0, description="Цена в магазине, $"),
    max_price: Decimal | None = Query(None, ge=0, description="Цена в магазине, $"),
    on_sale: bool = False,
    in_stock: bool = True,
    store: list[str] = Query([], description="Коды магазинов"),
    sort: catalog.Sort = "popular",
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
):
    f = catalog.ProductFilter(
        q=q, brands=brand, sizes=size, gender=gender, min_price=min_price, max_price=max_price,
        on_sale=on_sale, in_stock=in_stock, stores=store,
    )
    items, total = catalog.list_products(session, f, CalcSettings.load(session), sort, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/products/{product_id}", response_model=ProductDetail, summary="Карточка товара со всеми предложениями")
def get_product(product_id: int, session: SessionDep):
    product = catalog.get_product(session, product_id, CalcSettings.load(session))
    if product is None:
        raise HTTPException(404, "Товар не найден")
    return product


@router.get("/products/{product_id}/history", response_model=PriceHistoryOut, summary="История цен по магазинам")
def get_history(product_id: int, session: SessionDep, days: int = Query(90, ge=1, le=730)):
    history = catalog.price_history(session, product_id, days)
    if history is None:
        raise HTTPException(404, "Товар не найден")
    return history


@router.get("/filters", response_model=FiltersOut, summary="Значения для фильтров каталога")
def get_filters(session: SessionDep):
    return catalog.filters(session)


@router.get("/stores", response_model=list[StoreOut])
def list_stores(session: SessionDep):
    return session.scalars(select(Store).where(Store.is_active.is_(True)).order_by(Store.name)).all()


@router.get("/estimate-info", response_model=EstimateInfo, summary="Параметры расчёта цены «до двери»")
def estimate_info(session: SessionDep):
    s = CalcSettings.load(session)
    return {**{k: getattr(s, k) for k in EstimateInfo.model_fields if k != "disclaimer"}, "disclaimer": DISCLAIMER}
