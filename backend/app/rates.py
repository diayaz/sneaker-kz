"""Официальные курсы Национального банка РК (RSS) → таблица settings."""

import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Setting

log = logging.getLogger(__name__)

NBK_RSS_URL = "https://nationalbank.kz/rss/rates_all.xml"
CURRENCIES = {"USD": "usd_kzt_rate", "EUR": "eur_kzt_rate"}
# Защита от мусора: курс за день не меняется больше чем на 20%.
MAX_DAILY_CHANGE = Decimal("0.20")


class RatesError(RuntimeError):
    pass


def parse_nbk_rss(xml_text: str) -> dict[str, tuple[Decimal, date]]:
    """{"USD": (Decimal("441.88"), date(2026, 9, 26)), ...} — курс за 1 единицу валюты."""
    root = ET.fromstring(xml_text)
    rates = {}
    for item in root.iter("item"):
        code = (item.findtext("title") or "").strip()
        value = (item.findtext("description") or "").strip()
        if not code or not value:
            continue
        quant = Decimal((item.findtext("quant") or "1").strip() or "1")
        day = datetime.strptime((item.findtext("pubDate") or "").strip(), "%d.%m.%Y").date()
        rates[code] = (Decimal(value) / quant, day)
    return rates


def fetch_nbk_rates() -> dict[str, tuple[Decimal, date]]:
    from scrapers.http import PoliteClient

    client = PoliteClient(min_delay=0, max_delay=0)
    try:
        return parse_nbk_rss(client.get(NBK_RSS_URL).text)
    finally:
        client.close()


def apply_rates(session: Session, rates: dict[str, tuple[Decimal, date]]) -> dict[str, Decimal]:
    missing = set(CURRENCIES) - set(rates)
    if missing:
        raise RatesError(f"в RSS Нацбанка нет курсов: {', '.join(sorted(missing))}")

    settings = {s.key: s for s in session.query(Setting).filter(Setting.key.in_([*CURRENCIES.values(), "rates_date"]))}
    applied = {}
    for code, key in CURRENCIES.items():
        new, _ = rates[code]
        old = Decimal(settings[key].value) if key in settings and settings[key].value else None
        # Сравниваем только с курсом, пришедшим от Нацбанка: стартовые заглушки проверять не с чем.
        if old and settings.get("rates_date") and settings["rates_date"].value and abs(new - old) / old > MAX_DAILY_CHANGE:
            raise RatesError(f"{code}: курс {old} → {new} изменился больше чем на {MAX_DAILY_CHANGE:%}, не применяем")
        applied[code] = new.quantize(Decimal("0.01"))

    for code, key in CURRENCIES.items():
        settings[key].value = str(applied[code])
    settings["rates_date"].value = max(rates[c][1] for c in CURRENCIES).isoformat()
    session.commit()
    log.info("Курсы Нацбанка на %s: %s", settings["rates_date"].value, {c: str(v) for c, v in applied.items()})
    return applied


def update_rates(session: Session) -> dict[str, Decimal]:
    return apply_rates(session, fetch_nbk_rates())
