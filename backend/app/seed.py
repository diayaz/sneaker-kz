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
    "duty_free_limit_eur": ("200", "Беспошлинный лимит на посылку, €"),
    "duty_rate_pct": ("15", "Ставка пошлины на превышение лимита, %"),
    "duty_min_eur_per_kg": ("2", "Минимальная пошлина за кг веса, €"),
}


def seed_settings(session: Session) -> int:
    existing = {key for (key,) in session.query(Setting.key)}
    added = 0
    for key, (value, description) in DEFAULT_SETTINGS.items():
        if key not in existing:
            session.add(Setting(key=key, value=value, description=description))
            added += 1
    session.commit()
    return added
