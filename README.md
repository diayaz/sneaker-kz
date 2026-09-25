# Sneaker KZ — агрегатор цен на кроссовки

Показывает, где дешевле купить кроссовки в зарубежных магазинах, и считает
ориентировочную цену «до двери» в Казахстане. Мы ничего не продаём — только
показываем цены и ведём на сайт магазина.

## Структура

```
backend/
  app/            модели БД, конфиг, (позже) FastAPI
  scrapers/
    base.py       общий интерфейс парсера (BaseScraper, ScrapedProduct)
    http.py       «вежливый» HTTP-клиент: паузы 2–5 с, повторы, стоп при блокировке
    pipeline.py   сохранение: товары, предложения, размеры, история цен, журнал запусков
    stores/       один файл = один магазин, подключается автоматически
  migrations/     Alembic
  manage.py       командная строка
frontend/         Next.js (шаг 6)
```

## База

| Таблица | Что хранит |
|---|---|
| `stores` | магазин, страна, валюта, налог с продаж по умолчанию |
| `products` | артикул (уникальный, нормализованный), бренд, модель, название, цвет, картинка |
| `offers` | товар × магазин: цена, старая цена, наличие, ссылка, дата обновления |
| `offer_sizes` | размеры предложения и их наличие (отдельно — для фильтра по размеру) |
| `price_history` | цена предложения на каждый день |
| `settings` | курсы, тариф доставки, вес пары, лимит и ставка пошлины |
| `scrape_runs` | журнал запусков парсеров: собрано / ошибок / статус |

Товары из разных магазинов связываются по артикулу (`M990-GL6` → `M990GL6`).

## Запуск

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py init-db     # миграции + настройки по умолчанию
python manage.py stats
pytest
```

По умолчанию SQLite в `backend/data/`. Для PostgreSQL задайте `DATABASE_URL` в `backend/.env`
(см. `.env.example`).

## Магазины

Сейчас: Sneaker Politics, Social Status, Bodega, Shoe Palace (все на Shopify).
New Balance, Adidas и Amazon закрыты защитой от ботов — подробности и план в [docs/sources.md](docs/sources.md).

```bash
python manage.py scrape                      # все магазины
python manage.py scrape bodega_us            # один
```

Логи — в `backend/logs/scrape_<дата>.log`, итоги запусков — в таблице `scrape_runs` (`python manage.py stats`).

### Новый магазин

- **На Shopify** — файл в `backend/scrapers/stores/` с подклассом `ShopifyScraper`: `store`, `domain`
  и, если нужно, хуки `is_sneaker` / `gender` / `style_code` / `color` (примеры — соседние файлы).
- **Любой другой** — подкласс `BaseScraper` с `store = StoreInfo(...)` и `iter_products()`,
  отдающим `ScrapedProduct`. Сохранение, история цен и журнал — в `pipeline.py`.

Товары сопоставляются по артикулу без разделителей (`IQ6573-100` = `iq6573 100`);
артикулы короче 6 символов между магазинами не сопоставляются.
