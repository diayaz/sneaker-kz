import logging
import random
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
RETRY_STATUSES = {429, 500, 502, 503, 504}


class BlockedError(RuntimeError):
    """Сайт явно отказал в доступе (403 и т.п.). Обходить не пытаемся — останавливаемся и сообщаем."""


class PoliteClient:
    """HTTP-клиент с паузой 2–5 с между запросами и повторами при временных ошибках."""

    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        retries: int = 3,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        self.min_delay, self.max_delay, self.retries = min_delay, max_delay, retries
        self._last_request = 0.0
        self._client = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
                **(headers or {}),
            },
            timeout=timeout,
            follow_redirects=True,
        )

    def _wait(self) -> None:
        delay = random.uniform(self.min_delay, self.max_delay)
        remaining = self._last_request + delay - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        self._last_request = time.monotonic()

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(1, self.retries + 1):
            self._wait()
            try:
                resp = self._client.get(url, **kwargs)
            except httpx.TransportError as exc:
                log.warning("Сетевая ошибка (%s/%s) %s: %s", attempt, self.retries, url, exc)
                if attempt == self.retries:
                    raise
            else:
                if resp.status_code in (401, 403):
                    raise BlockedError(f"{resp.status_code} на {url}")
                if resp.status_code not in RETRY_STATUSES:
                    resp.raise_for_status()
                    return resp
                log.warning("HTTP %s (%s/%s) %s", resp.status_code, attempt, self.retries, url)
                if attempt == self.retries:
                    if resp.status_code == 429:
                        raise BlockedError(f"429 Too Many Requests на {url}")
                    resp.raise_for_status()
            time.sleep(10 * attempt)  # нарастающая пауза перед повтором
        raise AssertionError("unreachable")

    def get_json(self, url: str, **kwargs: Any) -> Any:
        return self.get(url, **kwargs).json()

    def close(self) -> None:
        self._client.close()
