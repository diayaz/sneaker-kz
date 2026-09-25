# Источники данных: что проверено

Дата проверки: 2026-09-25.

## Подключены (Shopify, публичный `/products.json`)

`robots.txt` этих магазинов запрещает только `/recommendations/products`. Цены запрашиваются
с `currency=USD` (без него Shopify пересчитывает в валюту страны посетителя, например в тенге).

| Код | Магазин | Артикул | Особенности |
|---|---|---|---|
| `sneakerpolitics_us` | sneakerpolitics.com | SKU `HQ2592-702\|7.5` | цвет после « - » в названии |
| `socialstatus_us` | socialstatuspgh.com | SKU | пол в тегах `mens`/`womens` |
| `bodega_us` | bdgastore.com | SKU | кроссовки — тег `sneakers`, цвет в опции Color |
| `shoepalace_us` | shoepalace.com | тег `STYLE_…` (SKU внутренний) | пол `Department_*`, много pre-release без наличия |

## Закрыты защитой — нужны официальные фиды

- **New Balance US** (newbalance.com) — Akamai: 403 на любые программные запросы и на headless-браузер,
  включая `robots.txt`. Каталог сайта идёт из Algolia, но ключ ограничен по Referer — не используем.
  В карточке `/pd/…` есть JSON-LD `ProductGroup` со всеми цветами/размерами/ценами и `productPricing`
  со старой ценой — пригодится, если появится разрешённый доступ.
- **Adidas US** (adidas.com) — Akamai WAF, то же поведение.
- **Amazon** — запрет сбора данных в Conditions of Use; официальный путь — Associates + Product Advertising API
  (доступ после первых продаж).

План: подать заявки в партнёрские программы New Balance и Adidas (Rakuten / CJ / Impact — уточнить),
получить товарные фиды и подключить их отдельными модулями в `scrapers/stores/`.

## Проверено попутно (не по теме кроссовок)

- magnum.kz — открытый API `magnum.kz:1337/api/new-product?city=…`, только акционные товары.
- small.kz — каталога с ценами нет, только акции и PDF; полный ассортимент в SmallFood/Glovo/Wolt/Яндекс.
