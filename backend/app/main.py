import json
import logging
import os
import time

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.db import AsyncSessionLocal, engine
from app.models import Base, Question

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


def _question_to_dict(q: Question) -> dict:
    return {
        "id": str(q.id),
        "version": q.version,
        "type": q.type,
        "subject": q.subject,
        "chapter": q.chapter,
        "topic": q.topic,
        "difficulty": q.difficulty,
        "exam_tag": q.exam_tag,
        "stem": q.stem,
        "options": q.options,
        "correct": q.correct,
        "explanation": q.explanation,
        "media": q.media,
        "language": q.language,
        "is_active": q.is_active,
    }


@app.get("/questions/{question_id}")
async def get_question(question_id: str):
    """
    Phase 2: cached read path.
    Cache key: q:{id}:v{version} — version baked into key so edits never serve stale data.
    Logs cache_hit/cache_miss and db_query_count per request.
    """
    t0 = time.perf_counter()

    # --- step 1: lookup current version from a lightweight version index ---
    # We store q:ver:{id} -> version so we can build the full key without hitting Postgres.
    # On a true miss this key won't exist yet; we fall through to Postgres.
    version_key = f"q:ver:{question_id}"
    version_str = await redis_client.get(version_key)

    if version_str is not None:
        cache_key = f"q:{question_id}:v{version_str}"
        payload = await redis_client.get(cache_key)
        if payload is not None:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(
                "get_question id=%s cache_hit=true db_query_count=0 elapsed_ms=%s",
                question_id, elapsed_ms,
            )
            return json.loads(payload)

    # --- step 2: Postgres fallback ---
    db_query_count = 0
    async with AsyncSessionLocal() as session:
        result = await session.get(Question, question_id)
        db_query_count = 1

    if result is None or not result.is_active:
        raise HTTPException(status_code=404, detail="question not found")

    data = _question_to_dict(result)

    # back-fill both keys
    cache_key = f"q:{question_id}:v{result.version}"
    await redis_client.set(f"q:ver:{question_id}", str(result.version))
    await redis_client.set(cache_key, json.dumps(data))
    # DEFERRED: set TTL when CDN / eviction policy is introduced

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "get_question id=%s cache_hit=false db_query_count=%d elapsed_ms=%s",
        question_id, db_query_count, elapsed_ms,
    )
    return data


@app.get("/debug/metrics")
async def debug_metrics():
    """Dump Redis info useful for observing cache behavior."""
    info = await redis_client.info("stats")
    keyspace = await redis_client.info("keyspace")
    return {
        "redis_keyspace_hits": info.get("keyspace_hits"),
        "redis_keyspace_misses": info.get("keyspace_misses"),
        "redis_hit_rate": round(
            info.get("keyspace_hits", 0)
            / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1),
            4,
        ),
        "keyspace": keyspace,
    }


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
