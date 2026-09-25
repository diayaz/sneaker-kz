import logging
from datetime import date

from app.config import config


def setup_logging(name: str = "app") -> None:
    """Пишет в консоль и в logs/<name>_<дата>.log."""
    config.log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    for handler in (
        logging.StreamHandler(),
        logging.FileHandler(config.log_dir / f"{name}_{date.today():%Y-%m-%d}.log", encoding="utf-8"),
    ):
        handler.setFormatter(fmt)
        root.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
