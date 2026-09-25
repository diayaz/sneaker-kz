from dataclasses import replace
from decimal import Decimal

from app.pricing import CalcSettings, calculate

D = Decimal
BASE = CalcSettings(
    usd_kzt_rate=D("450"),
    eur_kzt_rate=D("500"),
    rates_date="2026-09-26",
    shipping_usd_per_kg=D("12"),
    shoe_weight_kg=D("1.5"),
    duty_free_limit_eur=D("200"),
    duty_rate_pct=D("15"),
    duty_free_weight_kg=D("31"),
    duty_min_eur_per_kg=D("2"),
    duty_include_shipping=False,
)


def test_under_limit_no_duty():
    r = calculate(D("150"), D("0"), BASE)  # 150$ × 450/500 = 135€ < 200€
    assert r.shipping_usd == D("18.00")
    assert r.duty_eur == 0
    assert r.total_kzt == D("75600")  # (150 + 18) × 450


def test_over_limit_pays_15_percent_of_excess():
    r = calculate(D("300"), D("0"), BASE)  # 270€ → (270 − 200) × 15% = 10.50€
    assert r.customs_value_eur == D("270.00")
    assert r.duty_eur == D("10.50")
    assert r.duty_kzt == D("5250")
    assert r.total_kzt == D("135000") + D("8100") + D("5250")


def test_sales_tax_added_and_counts_for_customs():
    r = calculate(D("200"), D("10"), BASE)  # 220$ → 198€, всё ещё без пошлины
    assert r.sales_tax_usd == D("20.00")
    assert r.duty_eur == 0
    assert r.total_kzt == D("107100")  # (200 + 20 + 18) × 450


def test_shipping_in_customs_value_when_enabled():
    s = replace(BASE, duty_include_shipping=True)
    assert calculate(D("210"), D("0"), BASE).duty_eur == 0  # 189€
    assert calculate(D("210"), D("0"), s).duty_eur == D("0.78")  # (210+18)×0.9 = 205.20€ → 5.20 × 15%


def test_weight_rule_only_above_weight_limit():
    heavy = replace(BASE, shoe_weight_kg=D("33"))
    r = calculate(D("100"), D("0"), heavy)  # по стоимости 0, по весу (33 − 31) × 2€ = 4€
    assert r.duty_eur == D("4.00")
