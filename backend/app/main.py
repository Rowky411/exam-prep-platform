import json
import logging
import os
import random
import time

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text

from app.auth import get_current_user
from app.db import AsyncSessionLocal, engine
from app.models import Attempt, Base, Question, Test, User, UserStats

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


async def _fetch_questions_cached(
    question_ids: list[str],
) -> tuple[list[dict], int, int, int]:
    """
    Batch-fetch questions from Redis, falling back to a single Postgres query for misses.
    Returns (questions_in_order, cache_hits, cache_misses, db_query_count).

    Two-key pattern per question (same as Phase 2):
      q:ver:{id}        -> current version string
      q:{id}:v{version} -> serialized question payload
    Doing it in batch here means fetching a 20-question test costs ~2 Redis round-trips
    regardless of N, vs N round-trips if called one at a time.
    """
    if not question_ids:
        return [], 0, 0, 0

    # Round-trip 1: get all version keys at once
    ver_keys = [f"q:ver:{qid}" for qid in question_ids]
    versions = await redis_client.mget(*ver_keys)

    # Build payload keys for questions that have a cached version
    payload_keys: list[str | None] = []
    for qid, ver in zip(question_ids, versions):
        payload_keys.append(f"q:{qid}:v{ver}" if ver is not None else None)

    # Round-trip 2: batch-get all known payload keys
    existing_keys = [k for k in payload_keys if k is not None]
    raw_payloads = await redis_client.mget(*existing_keys) if existing_keys else []
    key_to_raw = dict(zip(existing_keys, raw_payloads))

    # Partition into hits and misses
    result_map: dict[str, dict] = {}
    miss_ids: list[str] = []
    cache_hits = cache_misses = 0

    for qid, pk in zip(question_ids, payload_keys):
        raw = key_to_raw.get(pk) if pk else None
        if raw is not None:
            result_map[qid] = json.loads(raw)
            cache_hits += 1
        else:
            miss_ids.append(qid)
            cache_misses += 1

    # One DB query for all misses — never N+1
    db_query_count = 0
    if miss_ids:
        async with AsyncSessionLocal() as session:
            stmt = select(Question).where(
                Question.id.in_(miss_ids),
                Question.is_active == True,
            )
            db_result = await session.execute(stmt)
            rows = db_result.scalars().all()
        db_query_count = 1

        for row in rows:
            data = _question_to_dict(row)
            qid_str = str(row.id)
            await redis_client.set(f"q:ver:{qid_str}", str(row.version))
            await redis_client.set(f"q:{qid_str}:v{row.version}", json.dumps(data))
            result_map[qid_str] = data

    questions = [result_map[qid] for qid in question_ids if qid in result_map]
    return questions, cache_hits, cache_misses, db_query_count


# ---------------------------------------------------------------------------
# Phase 2 — single question read
# ---------------------------------------------------------------------------

@app.get("/questions/{question_id}")
async def get_question(question_id: str):
    """
    Phase 2: cached read path.
    Cache key: q:{id}:v{version} — version baked in so edits never serve stale data.
    Logs cache_hit/cache_miss and db_query_count per request.
    """
    t0 = time.perf_counter()

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

    db_query_count = 0
    async with AsyncSessionLocal() as session:
        result = await session.get(Question, question_id)
        db_query_count = 1

    if result is None or not result.is_active:
        raise HTTPException(status_code=404, detail="question not found")

    data = _question_to_dict(result)
    await redis_client.set(f"q:ver:{question_id}", str(result.version))
    await redis_client.set(f"q:{question_id}:v{result.version}", json.dumps(data))
    # DEFERRED: set TTL when CDN / eviction policy is introduced

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "get_question id=%s cache_hit=false db_query_count=%d elapsed_ms=%s",
        question_id, db_query_count, elapsed_ms,
    )
    return data


# ---------------------------------------------------------------------------
# Phase 3 — test assembly
# ---------------------------------------------------------------------------

class TestCreate(BaseModel):
    title: str = "Untitled Test"
    subject: str | None = None
    chapter: str | None = None
    topic: str | None = None
    difficulty: int | None = None  # 1–5
    exam_tag: str | None = None
    count: int = 10


@app.post("/tests", status_code=201)
async def create_test(body: TestCreate):
    """
    Phase 3: test assembly.
    Queries the question bank with the supplied filters, randomly samples `count`
    questions, stores the ordered ID list as a Test row, and caches the metadata.

    A test is *just* an ID list — no question data is duplicated in the tests table.
    The question payloads are fetched (from cache) at read time in GET /tests/{id}.
    """
    t0 = time.perf_counter()

    # Build filter predicate from supplied fields only
    conditions = [Question.is_active == True]
    if body.subject:
        conditions.append(Question.subject == body.subject)
    if body.chapter:
        conditions.append(Question.chapter == body.chapter)
    if body.topic:
        conditions.append(Question.topic == body.topic)
    if body.difficulty is not None:
        conditions.append(Question.difficulty == body.difficulty)
    if body.exam_tag:
        conditions.append(Question.exam_tag == body.exam_tag)

    # Fetch only IDs — avoids pulling full question rows for assembly
    async with AsyncSessionLocal() as session:
        stmt = select(Question.id).where(*conditions)
        db_result = await session.execute(stmt)
        all_ids = [str(row[0]) for row in db_result.all()]
    db_query_count = 1

    if not all_ids:
        raise HTTPException(status_code=404, detail="no questions match filters")

    selected_ids = random.sample(all_ids, min(body.count, len(all_ids)))

    filters = {k: v for k, v in body.model_dump(exclude={"title", "count"}).items() if v is not None}

    test = Test(title=body.title, question_ids=selected_ids, filters=filters)
    async with AsyncSessionLocal() as session:
        session.add(test)
        await session.commit()
        await session.refresh(test)
    db_query_count += 1

    test_data = {
        "id": str(test.id),
        "title": test.title,
        "question_ids": test.question_ids,
        "filters": test.filters,
        "created_at": test.created_at.isoformat(),
    }
    # Cache test metadata so GET /tests/{id} skips Postgres on warm reads
    await redis_client.set(f"t:{test.id}", json.dumps(test_data))

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "create_test id=%s question_count=%d db_query_count=%d elapsed_ms=%s",
        test.id, len(selected_ids), db_query_count, elapsed_ms,
    )
    return test_data


@app.get("/tests/{test_id}")
async def get_test(test_id: str):
    """
    Phase 3: serve a test with all question payloads.
    Test metadata: Redis t:{id} → Postgres (1 query on miss, 0 on hit).
    Questions: batch Redis lookup → single Postgres query for any misses.

    On first fetch: db_query_count ≤ 2 (test + missing questions).
    On subsequent fetches: db_query_count = 0.
    """
    t0 = time.perf_counter()
    db_query_count = 0

    # Step 1: fetch test metadata
    test_payload = await redis_client.get(f"t:{test_id}")

    if test_payload is not None:
        test_data = json.loads(test_payload)
        test_cache_hit = True
    else:
        async with AsyncSessionLocal() as session:
            test = await session.get(Test, test_id)
        db_query_count += 1

        if test is None:
            raise HTTPException(status_code=404, detail="test not found")

        test_data = {
            "id": str(test.id),
            "title": test.title,
            "question_ids": test.question_ids,
            "filters": test.filters,
            "created_at": test.created_at.isoformat(),
        }
        await redis_client.set(f"t:{test_id}", json.dumps(test_data))
        test_cache_hit = False

    # Step 2: batch-fetch all questions (cache → DB for misses)
    questions, q_hits, q_misses, q_db = await _fetch_questions_cached(test_data["question_ids"])
    db_query_count += q_db

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "get_test id=%s test_cache_hit=%s q_cache_hits=%d q_cache_misses=%d db_query_count=%d elapsed_ms=%s",
        test_id, test_cache_hit, q_hits, q_misses, db_query_count, elapsed_ms,
    )

    return {
        "id": test_data["id"],
        "title": test_data["title"],
        "filters": test_data["filters"],
        "created_at": test_data["created_at"],
        "question_count": len(questions),
        "questions": questions,
    }


# ---------------------------------------------------------------------------
# Phase 5 — write path
# ---------------------------------------------------------------------------

QUEUE_KEY = "queue:attempts"


def _score_answer(selected: dict, correct: dict, qtype: str) -> bool:
    """Score one answer. Pure function — used by both sync endpoint and worker."""
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


class AnswerItem(BaseModel):
    question_id: str
    question_version: int
    selected: dict  # {"id":"b"} | {"ids":["a","c"]} | {"value":"42"}


class SubmitAttempts(BaseModel):
    test_id: str | None = None
    answers: list[AnswerItem]


@app.post("/attempts/sync", status_code=201)
async def submit_attempts_sync(
    body: SubmitAttempts,
    current_user: User = Depends(get_current_user),
):
    """
    Phase 5a: synchronous write path.
    Fetches questions, scores every answer inline, writes attempts + user_stats
    before returning. Intentionally slow under load — the baseline to beat in 5b.
    """
    t0 = time.perf_counter()

    if not body.answers:
        raise HTTPException(status_code=422, detail="answers list is empty")

    # Fetch all questions (cache → DB batch)
    qids = [a.question_id for a in body.answers]
    questions, _, _, db_q = await _fetch_questions_cached(qids)
    q_map = {q["id"]: q for q in questions}

    # Score each answer
    results = []
    for ans in body.answers:
        q = q_map.get(ans.question_id)
        if q is None:
            continue
        correct = _score_answer(ans.selected, q["correct"], q["type"])
        results.append({"question_id": ans.question_id, "is_correct": correct, "topic": q["topic"]})

    # Write attempts rows (all scored immediately)
    import uuid as _uuid
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    attempt_rows = []
    for ans, res in zip(body.answers, results):
        attempt_rows.append(Attempt(
            id=_uuid.uuid4(),
            user_id=current_user.clerk_id,
            test_id=body.test_id,
            question_id=ans.question_id,
            question_version=ans.question_version,
            selected=ans.selected,
            is_correct=res["is_correct"],
            scored_at=now,
        ))

    # Upsert user_stats
    async with AsyncSessionLocal() as session:
        session.add_all(attempt_rows)

        stats = await session.get(UserStats, current_user.clerk_id)
        if stats is None:
            stats = UserStats(user_id=current_user.clerk_id, total_attempted=0, total_correct=0, accuracy_by_topic={})
            session.add(stats)

        stats.total_attempted += len(results)
        stats.total_correct += sum(1 for r in results if r["is_correct"])

        acc = dict(stats.accuracy_by_topic or {})
        for r in results:
            t = acc.setdefault(r["topic"], {"attempted": 0, "correct": 0})
            t["attempted"] += 1
            if r["is_correct"]:
                t["correct"] += 1
        stats.accuracy_by_topic = acc

        await session.commit()

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    total = len(results)
    correct = sum(1 for r in results if r["is_correct"])
    logger.info(
        "submit_sync user=%s answers=%d correct=%d db_query_count=%d elapsed_ms=%s",
        current_user.clerk_id, total, correct, db_q + 1, elapsed_ms,
    )

    return {
        "mode": "sync",
        "elapsed_ms": elapsed_ms,
        "score": {"correct": correct, "total": total, "pct": round(correct / max(total, 1) * 100, 1)},
        "results": [{"question_id": r["question_id"], "is_correct": r["is_correct"]} for r in results],
    }


@app.post("/attempts", status_code=202)
async def submit_attempts_async(
    body: SubmitAttempts,
    current_user: User = Depends(get_current_user),
):
    """
    Phase 5b: async write path.
    Writes unscored attempt rows immediately, pushes one job per attempt onto
    the Redis queue, then returns. The worker process scores them in the background.
    This endpoint stays fast regardless of how many answers are submitted.
    """
    t0 = time.perf_counter()

    if not body.answers:
        raise HTTPException(status_code=422, detail="answers list is empty")

    import uuid as _uuid

    # Persist unscored attempts
    attempt_rows = [
        Attempt(
            id=_uuid.uuid4(),
            user_id=current_user.clerk_id,
            test_id=body.test_id,
            question_id=ans.question_id,
            question_version=ans.question_version,
            selected=ans.selected,
            is_correct=None,   # scored by worker
            scored_at=None,
        )
        for ans in body.answers
    ]

    async with AsyncSessionLocal() as session:
        session.add_all(attempt_rows)
        await session.commit()

    # Push one job per attempt onto the Redis queue
    jobs = [
        json.dumps({
            "attempt_id": str(row.id),
            "question_id": str(row.question_id),
            "question_version": row.question_version,
            "selected": row.selected,
            "user_id": current_user.clerk_id,
        })
        for row in attempt_rows
    ]
    await redis_client.rpush(QUEUE_KEY, *jobs)

    queue_depth = await redis_client.llen(QUEUE_KEY)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info(
        "submit_async user=%s queued=%d queue_depth=%d elapsed_ms=%s",
        current_user.clerk_id, len(jobs), queue_depth, elapsed_ms,
    )

    return {
        "mode": "async",
        "elapsed_ms": elapsed_ms,
        "queued": len(jobs),
        "queue_depth": queue_depth,
        "attempt_ids": [str(r.id) for r in attempt_rows],
    }


@app.get("/leaderboard")
async def leaderboard(limit: int = 10):
    """Phase 6: top users by total_correct, used to verify worker is updating stats under load."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(UserStats)
            .where(UserStats.total_attempted > 0)
            .order_by(UserStats.total_correct.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
    return [
        {
            "rank": i + 1,
            "user_id": r.user_id,
            "total_attempted": r.total_attempted,
            "total_correct": r.total_correct,
            "accuracy": round(r.total_correct / max(r.total_attempted, 1) * 100, 1),
        }
        for i, r in enumerate(rows)
    ]


@app.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "clerk_id": current_user.clerk_id,
        "email": current_user.email,
        "role": current_user.role,
    }


@app.get("/users/{user_id}/stats")
async def get_user_stats(
    user_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.clerk_id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    async with AsyncSessionLocal() as session:
        stats = await session.get(UserStats, user_id)
    if stats is None:
        return {"user_id": user_id, "total_attempted": 0, "total_correct": 0, "accuracy_by_topic": {}}
    return {
        "user_id": stats.user_id,
        "total_attempted": stats.total_attempted,
        "total_correct": stats.total_correct,
        "accuracy": round(stats.total_correct / max(stats.total_attempted, 1) * 100, 1),
        "accuracy_by_topic": stats.accuracy_by_topic,
        "updated_at": stats.updated_at.isoformat() if stats.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

@app.get("/debug/metrics")
async def debug_metrics():
    """Dump Redis info useful for observing cache behavior."""
    info = await redis_client.info("stats")
    keyspace = await redis_client.info("keyspace")
    queue_depth = await redis_client.llen(QUEUE_KEY)
    return {
        "redis_keyspace_hits": info.get("keyspace_hits"),
        "redis_keyspace_misses": info.get("keyspace_misses"),
        "redis_hit_rate": round(
            info.get("keyspace_hits", 0)
            / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1),
            4,
        ),
        "queue_depth": queue_depth,
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
