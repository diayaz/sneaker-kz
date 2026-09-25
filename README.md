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

## API

```bash
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Документация: http://localhost:8000/docs. Все маршруты под `/api/v1` — их же будут использовать мобильные приложения.

| Маршрут | Что отдаёт |
|---|---|
| `GET /products` | поиск и каталог: `q`, `brand`, `size`, `gender`, `min_price`/`max_price` ($), `on_sale`, `in_stock`, `store`, `sort` (`popular`, `price_asc`, `price_desc`, `discount`, `new`), `page`, `page_size` |
| `GET /products/{id}` | карточка: предложения всех магазинов с размерами и расчётом «до двери» |
| `GET /products/{id}/history?days=90` | история цен по магазинам |
| `GET /filters` | бренды, размеры, диапазон цен для фильтров |
| `GET /stores` | магазины |
| `GET /estimate-info` | курсы и параметры расчёта + текст оговорки |

**Расчёт «до двери»** ([app/pricing.py](backend/app/pricing.py)): (цена + налог штата + доставка
посредника) × курс USD + пошлина × курс EUR. Пошлина — 15% с превышения €200 на посылку
(€2/кг сверх 31 кг, если больше). Все параметры — в таблице `settings`.

## Фронтенд

Next.js 16 (App Router, TypeScript, Tailwind), папка `frontend/`. Страницы рендерятся на сервере
и берут данные из API (кэш 5 минут).

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000, API должен работать на :8000
```

Адрес API — переменная `API_URL` (по умолчанию `http://127.0.0.1:8000`).
Все тексты интерфейса — в `frontend/lib/i18n/ru.ts` (для казахского — такой же файл `kk.ts`).

| Страница | Что на ней |
|---|---|
| `/` | поиск, популярные бренды, популярные модели, лучшие скидки, курс Нацбанка |
| `/catalog` | фильтры (пол, размер, цена, скидка, бренд), сортировка, пагинация; всё в URL |
| `/product/[id]` | цены во всех магазинах с расчётом «до двери», размеры, кнопка в магазин, график цены |

## Ежедневное обновление

`python manage.py daily` — курсы USD/EUR с RSS Нацбанка РК, затем все парсеры. Падение одного
магазина или курсов не останавливает остальное, но команда вернёт код 1. Если курс за день
изменился больше чем на 20%, он не применяется (защита от мусора в источнике).

**Windows (локально):** `powershell -ExecutionPolicy Bypass -File scripts\register_task.ps1 [-Time 07:00]` —
задача «SneakerKZ Daily» в Планировщике; если компьютер был выключен, запустится при включении.
Удалить: `Unregister-ScheduledTask -TaskName "SneakerKZ Daily" -Confirm:$false`.

**Linux-сервер (cron):**
```
0 7 * * * cd /srv/sneaker-kz/backend && .venv/bin/python manage.py daily >> logs/cron.log 2>&1
```

Лог каждого запуска — `backend/logs/daily_<дата>.log`.

### Новый магазин

- **На Shopify** — файл в `backend/scrapers/stores/` с подклассом `ShopifyScraper`: `store`, `domain`
  и, если нужно, хуки `is_sneaker` / `gender` / `style_code` / `color` (примеры — соседние файлы).
- **Любой другой** — подкласс `BaseScraper` с `store = StoreInfo(...)` и `iter_products()`,
  отдающим `ScrapedProduct`. Сохранение, история цен и журнал — в `pipeline.py`.

Товары сопоставляются по артикулу без разделителей (`IQ6573-100` = `iq6573 100`);
артикулы короче 6 символов между магазинами не сопоставляются.
