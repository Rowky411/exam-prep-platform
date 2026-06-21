import logging
import os
import time

import redis.asyncio as aioredis
from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
from app.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("examprep")

REDIS_URL = os.environ["REDIS_URL"]

redis_client: aioredis.Redis | None = None

app = FastAPI(title="Exam Prep API")


@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

    # Create all tables if they don't exist yet
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await redis_client.ping()
    logger.info("startup: postgres=ok redis=ok tables=created")


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()
    if redis_client:
        await redis_client.aclose()


@app.get("/health")
async def health():
    """Phase 0 verify: returns 200 with postgres + redis status."""
    t0 = time.perf_counter()

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pg_status = "ok"
    except Exception as e:
        pg_status = f"error: {e}"

    try:
        await redis_client.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {e}"

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    ok = pg_status == "ok" and redis_status == "ok"

    logger.info("health check postgres=%s redis=%s elapsed_ms=%s", pg_status, redis_status, elapsed_ms)

    return {
        "status": "ok" if ok else "degraded",
        "postgres": pg_status,
        "redis": redis_status,
        "elapsed_ms": elapsed_ms,
    }
