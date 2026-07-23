"""
App entrypoint. Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8080
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_pool, close_pool
from app.telegram.webhook import router as telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="GBP AI Agent Backend", lifespan=lifespan)

app.include_router(telegram_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
