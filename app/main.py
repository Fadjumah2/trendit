"""
App entrypoint. Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8080
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_pool, close_pool
from app.telegram.webhook import router as telegram_router
from app.internal import router as internal_router
from app.routes.approval import router as approval_router
from app.routes.oauth import router as oauth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="Trendit", lifespan=lifespan)

app.include_router(telegram_router)
app.include_router(internal_router)
app.include_router(approval_router)
app.include_router(oauth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/db")
async def debug_db():
    from app.db import _pool, get_pool
    if _pool is None:
        return {"pool_initialized": False}
    try:
        pool = get_pool()
        res = await pool.fetchval("SELECT 1")
        
        # Check tables and counts
        tables = await pool.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        counts = {}
        for t in tables:
            name = t["table_name"]
            count = await pool.fetchval(f"SELECT COUNT(*) FROM {name}")
            counts[name] = count
            
        return {
            "pool_initialized": True, 
            "query_success": res == 1,
            "tables": [t["table_name"] for t in tables],
            "row_counts": counts
        }
    except Exception as e:
        return {"pool_initialized": True, "query_error": str(e)}
