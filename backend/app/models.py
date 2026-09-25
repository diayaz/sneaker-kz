from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

Money = Numeric(12, 2)


def utcnow() -> datetime:
    return datetime.now(UTC)


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)  # "newbalance_us"
    name: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(2))  # ISO: "US"
    currency: Mapped[str] = mapped_column(String(3))  # ISO: "USD"
    default_sales_tax_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    website: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    offers: Mapped[list["Offer"]] = relationship(back_populates="store")


class Product(Base):
    """Модель в конкретной расцветке. Одинаковые товары из разных магазинов сводятся по match_key."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    style_code: Mapped[str] = mapped_column(String(50))  # для показа, как в магазине: "IQ6573-100"
    match_key: Mapped[str] = mapped_column(String(50), unique=True)  # для сопоставления: "IQ6573100"
    brand: Mapped[str] = mapped_column(String(50), index=True)
    model: Mapped[str | None] = mapped_column(String(100), index=True)  # "990v6"
    name: Mapped[str] = mapped_column(String(255))
    color: Mapped[str | None] = mapped_column(String(100))
    gender: Mapped[str | None] = mapped_column(String(10))  # men / women / unisex
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    offers: Mapped[list["Offer"]] = relationship(back_populates="product")


class Offer(Base):
    """Предложение конкретного магазина по конкретному товару."""

    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("product_id", "store_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    price: Mapped[Decimal] = mapped_column(Money)
    old_price: Mapped[Decimal | None] = mapped_column(Money)  # зачёркнутая цена, если есть скидка
    currency: Mapped[str] = mapped_column(String(3))
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    url: Mapped[str] = mapped_column(Text)
    store_product_id: Mapped[str | None] = mapped_column(String(100))  # внутренний id в магазине
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product: Mapped[Product] = relationship(back_populates="offers")
    store: Mapped[Store] = relationship(back_populates="offers")
    sizes: Mapped[list["OfferSize"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan", order_by="OfferSize.sort_key"
    )
    history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan", order_by="PriceHistory.day"
    )


class OfferSize(Base):
    """Размеры отдельной таблицей, чтобы фильтр «есть 42.5» был обычным индексируемым запросом."""

    __tablename__ = "offer_sizes"
    __table_args__ = (UniqueConstraint("offer_id", "size", "width"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), index=True)
    size: Mapped[str] = mapped_column(String(10), index=True)  # US-размер как в магазине: "9.5"
    width: Mapped[str] = mapped_column(String(10), default="")  # у NB бывает D / 2E / 4E
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_key: Mapped[float] = mapped_column(default=0.0)

    offer: Mapped[Offer] = relationship(back_populates="sizes")


class PriceHistory(Base):
    """Одна запись на предложение в день — последняя цена за этот день."""

    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("offer_id", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date)
    price: Mapped[Decimal] = mapped_column(Money)
    old_price: Mapped[Decimal | None] = mapped_column(Money)
    in_stock: Mapped[bool] = mapped_column(Boolean)

    offer: Mapped[Offer] = relationship(back_populates="history")


class Setting(Base):
    """Параметры калькулятора, редактируются вручную (курс обновляется автоматически)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ScrapeRun(Base):
    """Журнал запусков парсеров: сколько собрано, сколько ошибок."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")  # running / ok / partial / failed
    items_ok: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    marked_out_of_stock: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
