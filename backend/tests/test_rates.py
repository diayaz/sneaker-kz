from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import sessionmaker

from app.db import Base, make_engine
from app.models import Setting
from app.rates import RatesError, apply_rates, parse_nbk_rss
from app.seed import seed_settings

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel>
  <item><title>USD</title><pubDate>26.09.2026</pubDate><description>441.88</description><quant>1</quant></item>
  <item><title>EUR</title><pubDate>26.09.2026</pubDate><description>502.5</description><quant>1</quant></item>
  <item><title>JPY</title><pubDate>26.09.2026</pubDate><description>297.1</description><quant>100</quant></item>
</channel></rss>"""


@pytest.fixture
def session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as s:
        seed_settings(s)
        yield s


def values(session):
    return {s.key: s.value for s in session.query(Setting)}


def test_parse_divides_by_quant():
    rates = parse_nbk_rss(RSS)
    assert rates["USD"] == (Decimal("441.88"), date(2026, 9, 26))
    assert rates["JPY"][0] == Decimal("2.971")


def test_first_update_replaces_placeholders(session):
    apply_rates(session, parse_nbk_rss(RSS))
    v = values(session)
    assert (v["usd_kzt_rate"], v["eur_kzt_rate"], v["rates_date"]) == ("441.88", "502.50", "2026-09-26")


def test_implausible_jump_rejected(session):
    apply_rates(session, parse_nbk_rss(RSS))
    broken = parse_nbk_rss(RSS.replace("441.88", "44.19"))
    with pytest.raises(RatesError):
        apply_rates(session, broken)
    assert values(session)["usd_kzt_rate"] == "441.88"


def test_missing_currency_rejected(session):
    only_usd = {"USD": (Decimal("441.88"), date(2026, 9, 26))}
    with pytest.raises(RatesError):
        apply_rates(session, only_usd)
