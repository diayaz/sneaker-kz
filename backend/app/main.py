"""FastAPI-приложение.  Запуск:  uvicorn app.main:app --reload  (из папки backend)"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import config

app = FastAPI(
    title="Sneaker KZ API",
    description="Цены на кроссовки в зарубежных магазинах и оценка стоимости «до двери» в Казахстане.",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins, allow_methods=["GET"], allow_headers=["*"])
app.include_router(router)


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
