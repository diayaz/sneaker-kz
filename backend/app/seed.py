"""Начальные значения настроек. Существующие значения не перезаписываются — их правят вручную."""

from sqlalchemy.orm import Session

from app.models import Setting

DEFAULT_SETTINGS: dict[str, tuple[str, str]] = {
    # Курсы обновляются ежедневно с сайта Нацбанка РК; здесь только стартовые заглушки.
    "usd_kzt_rate": ("500", "Курс USD/KZT (Нацбанк РК, обновляется ежедневно)"),
    "eur_kzt_rate": ("580", "Курс EUR/KZT (Нацбанк РК, нужен для лимита пошлины)"),
    "rates_date": ("", "Дата, на которую действуют курсы"),
    "shipping_usd_per_kg": ("12", "Примерный тариф посредника США→Казахстан, $ за кг"),
    "shoe_weight_kg": ("1.5", "Вес пары кроссовок с коробкой, кг"),
    "duty_free_limit_eur": ("200", "Беспошлинный лимит стоимости на посылку, €"),
    "duty_rate_pct": ("15", "Пошлина с превышения лимита стоимости, %"),
    "duty_free_weight_kg": ("31", "Беспошлинный лимит веса на посылку, кг"),
    "duty_min_eur_per_kg": ("2", "Пошлина за каждый кг сверх лимита веса, € (если больше, чем по стоимости)"),
    "duty_include_shipping": ("0", "1 — включать доставку в таможенную стоимость, 0 — только цену товара"),
}


def seed_settings(session: Session) -> int:
    """Добавляет недостающие настройки. Значения существующих не трогает, описания обновляет."""
    existing = {s.key: s for s in session.query(Setting)}
    added = 0
    for key, (value, description) in DEFAULT_SETTINGS.items():
        if key not in existing:
            session.add(Setting(key=key, value=value, description=description))
            added += 1
        elif existing[key].description != description:
            existing[key].description = description
    session.commit()
    return added
