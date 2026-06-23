#!/usr/bin/env python3
"""
Phase 5b worker — drains queue:attempts, scores each attempt, updates user_stats.
Separate process from the API: demonstrates the async write path.

Run via Docker Compose:
    docker compose up worker

Or directly:
    DATABASE_URL=... REDIS_URL=... python worker.py
"""
import asyncio
import json
import logging
import os
import time

import asyncpg
import redis.asyncio as aioredis

REDIS_URL = os.environ["REDIS_URL"]
DATABASE_URL = os.environ["DATABASE_URL"]
QUEUE_KEY = "queue:attempts"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s worker %(message)s",
)
logger = logging.getLogger("worker")


def _score(selected: dict, correct: dict, qtype: str) -> bool:
    if qtype in ("single_mcq", "true_false"):
        return selected.get("id") == correct.get("id")
    if qtype == "multi_mcq":
        return set(selected.get("ids", [])) == set(correct.get("ids", []))
    if qtype == "numerical":
        try:
            sv = float(selected.get("value", ""))
            cv = float(correct["value"])
            tol = float(correct.get("tolerance", 0.01))
            return abs(sv - cv) <= tol
        except (ValueError, TypeError, KeyError):
            return False
    return False


async def _fetch_question(qid: str, redis_client, pg_pool) -> dict | None:
    """Redis cache → Postgres fallback. Same key pattern as the API."""
    ver = await redis_client.get(f"q:ver:{qid}")
    if ver is not None:
        payload = await redis_client.get(f"q:{qid}:v{ver}")
        if payload is not None:
            return json.loads(payload)

    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, version, type, topic, correct FROM questions WHERE id=$1 AND is_active=true",
            qid,
        )
    if row is None:
        return None

    data = {
        "id": str(row["id"]),
        "version": row["version"],
        "type": row["type"],
        "topic": row["topic"],
        "correct": row["correct"],  # asyncpg decodes JSONB → dict automatically
    }
    await redis_client.set(f"q:ver:{qid}", str(row["version"]))
    await redis_client.set(f"q:{qid}:v{row['version']}", json.dumps(data))
    return data


async def _process_job(job: dict, redis_client, pg_pool) -> None:
    t0 = time.perf_counter()

    attempt_id = job["attempt_id"]
    qid = job["question_id"]
    selected = job["selected"]
    user_id = job["user_id"]

    question = await _fetch_question(qid, redis_client, pg_pool)
    if question is None:
        logger.warning("skip attempt=%s: question %s not found", attempt_id, qid)
        return

    is_correct = _score(selected, question["correct"], question["type"])
    topic = question.get("topic", "unknown")

    async with pg_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE attempts SET is_correct=$1, scored_at=NOW() WHERE id=$2",
                is_correct, attempt_id,
            )

            row = await conn.fetchrow(
                "SELECT total_attempted, total_correct, accuracy_by_topic FROM user_stats WHERE user_id=$1",
                user_id,
            )
            if row is None:
                acc = {topic: {"attempted": 1, "correct": int(is_correct)}}
                await conn.execute(
                    """INSERT INTO user_stats (user_id, total_attempted, total_correct, accuracy_by_topic, updated_at)
                       VALUES ($1, 1, $2, $3, NOW())""",
                    user_id, int(is_correct), acc,
                )
            else:
                # row["accuracy_by_topic"] is already a dict thanks to the jsonb codec
                acc = dict(row["accuracy_by_topic"] or {})
                t_stats = acc.setdefault(topic, {"attempted": 0, "correct": 0})
                t_stats["attempted"] += 1
                if is_correct:
                    t_stats["correct"] += 1
                await conn.execute(
                    """UPDATE user_stats
                       SET total_attempted = total_attempted + 1,
                           total_correct   = total_correct + $1,
                           accuracy_by_topic = $2,
                           updated_at = NOW()
                       WHERE user_id = $3""",
                    int(is_correct), acc, user_id,
                )

    queue_depth = await redis_client.llen(QUEUE_KEY)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "scored attempt=%s correct=%s queue_depth=%d elapsed_ms=%s",
        attempt_id, is_correct, queue_depth, elapsed_ms,
    )


async def _init_pg_conn(conn) -> None:
    # asyncpg returns JSONB as raw strings by default; format='text' required for the codec to fire
    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog", format="text")


async def main() -> None:
    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5, init=_init_pg_conn)
    logger.info("worker ready — listening on %s", QUEUE_KEY)

    while True:
        try:
            item = await redis_client.blpop(QUEUE_KEY, timeout=5)
            if item is None:
                continue  # timeout — loop again
            _, raw = item
            job = json.loads(raw)
            await _process_job(job, redis_client, pg_pool)
        except Exception as exc:
            logger.exception("error processing job: %s", exc)


if __name__ == "__main__":
    asyncio.run(main())
