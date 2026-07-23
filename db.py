"""
Shared asyncpg connection pool. Every service module (credentials, content
profile, post history) pulls connections from here rather than opening its
own — one pool per process, created on app startup, closed on shutdown.
"""
import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=1,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call init_pool() on app startup first")
    return _pool
