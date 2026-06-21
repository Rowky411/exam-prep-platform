# Exam-Prep MVP — Architecture Brief & Build Plan

> Drop this file in the repo root. Claude Code reads it every session — it is the shared
> source of truth for **what we're building, why, and in what order**. Keep it updated as
> the build progresses.

---

## 1. Purpose of this project

This is a **learning MVP**, not a production system. Its job is to make the core mechanisms
of a scalable exam-prep platform **visible and touchable** at small scale. Success = the
developer can run the system, generate load, and *watch* each mechanism work.

Optimize every decision for **clarity and observability**, never for scale or polish.

---

## 2. The one architectural principle that governs everything

Separate **static content** from **dynamic user state**. They have opposite characteristics
and are stored, served, and scaled differently:

- **Questions** — read-heavy, near-immutable, *shared by every user*. Treated as a cacheable
  asset keyed by `question_id + version`.
- **Attempts** — write-heavy, *unique per user*. Recorded fast, then scored/aggregated
  asynchronously.

Reads (questions) and writes (attempts) must never share a hot path. If you find yourself
fetching a question through the same code that writes an answer, stop and split them.

```
Client
  ├── READ path  → CDN(skipped) → Redis cache → Postgres question bank   [static, shared]
  └── WRITE path → Attempt API  → Redis queue  → worker → attempts/stats  [dynamic, per-user]
```

---

## 3. Guiding principles for this build

1. **Build the architecture, fake the ops.** Keep every architecturally instructive piece;
   skip operationally heavy ones. Localhost Redis teaches the same lesson a CDN does.
2. **Instrument everything.** Every cache hit/miss, DB query count per request, and queue
   depth must be logged. The learning is in *observing*, not just writing the code.
3. **Vertical slices.** Build one runnable phase at a time. Do not start a phase until the
   previous one runs and has been poked at.
4. **No premature abstraction.** Smallest thing that demonstrates the mechanism wins.

---

## 4. Tech stack

| Layer        | Choice                                   | Notes |
|--------------|------------------------------------------|-------|
| Backend      | FastAPI (Python 3.11+)                    | One service for now |
| Source of truth | PostgreSQL                            | `jsonb` for flexible question bodies |
| Cache + queue| Redis                                     | Cache layer AND the job queue |
| Worker       | A simple Redis-backed worker (RQ or a hand-rolled loop) | Must be a *separate process* from the API |
| Frontend     | React + Vite                              | One question renderer driven by `type` |
| Math render  | KaTeX (client-side)                       | Questions store Markdown + LaTeX, never HTML |
| Orchestration| Docker Compose                            | `docker compose up` brings up the whole system |
| Load testing | k6 or Locust                              | Used in the final phase |

---

## 5. Deliberate deferrals — do NOT build these yet

These are real production needs but add ops complexity without teaching new mechanisms.
Leave clear `# DEFERRED:` comments where they'd eventually go.

- CDN (localhost only for now)
- Elasticsearch / dedicated search index → use Postgres indexes + full-text search
- Authentication / real users → a hardcoded or header-supplied `user_id` is fine
- Cloud infra, autoscaling, Kubernetes
- Anti-piracy, watermarking, payments
- Offline packs (this is optional Phase 7, not core)

---

## 6. Data model

### `questions`
| column        | type      | notes |
|---------------|-----------|-------|
| id            | uuid (pk) | |
| version       | int       | bumped on edit; part of the cache key |
| type          | text      | `single_mcq` \| `multi_mcq` \| `true_false` \| `numerical` |
| subject       | text      | taxonomy |
| chapter       | text      | taxonomy |
| topic         | text      | taxonomy |
| difficulty    | int       | 1–5 |
| exam_tag      | text      | e.g. `HSC`, `admission`, `BCS` |
| stem          | text      | Markdown + LaTeX |
| options       | jsonb     | `[{id, text}]` (null for numerical) |
| correct       | jsonb     | answer key |
| explanation   | text      | Markdown + LaTeX |
| media         | jsonb     | `[url, ...]` (object-storage URLs; local paths fine for MVP) |
| language      | text      | |
| is_active     | bool      | soft delete |
| created_at / updated_at | timestamptz | |

Index on `(subject, chapter, topic, difficulty, exam_tag)` for test assembly.

### `tests` (an assembled test = an ordered list of question IDs)
`id`, `title`, `question_ids jsonb`, `filters jsonb`, `created_at`

### `attempts`
`id`, `user_id`, `test_id`, `question_id`, `question_version`, `selected jsonb`,
`is_correct bool NULL` (null until scored), `submitted_at`, `scored_at NULL`

### `user_stats` (precomputed by the worker)
`user_id`, `total_attempted`, `total_correct`, `accuracy_by_topic jsonb`, `updated_at`

---

## 7. Contracts to honor

**Cache contract.** Key = `q:{id}:v{version}` → serialized question payload (JSON).
Long TTL. On edit, bump `version` → a *new key* is written, so cache invalidation is free
and stale reads are impossible. Reads check Redis first; a miss falls through to Postgres
and back-fills the cache.

**Async write contract.** On submit: (1) write raw `attempts` rows immediately as
*unscored*, (2) push a job to the Redis queue, (3) return fast. A separate worker process
scores attempts and updates `user_stats`. The API never scores synchronously (except in
Phase 5a below, on purpose, so the difference can be felt).

**Instrumentation contract.** Structured logs must include, per request: `cache_hit`/`cache_miss`,
`db_query_count`. The worker logs `queue_depth` and per-job processing time. Expose a
`/debug/metrics` endpoint that dumps these counters.

---

## 8. Build phases

Each phase is independently runnable. Finish and verify before moving on. **Commit after
each working phase.**

### Phase 0 — Skeleton
- Docker Compose with Postgres + Redis; FastAPI app boots; healthcheck endpoint.
- **Verify:** `docker compose up` → `GET /health` returns 200.

### Phase 1 — Data model + seed
- Create the `questions` schema and a seed script loading ~300 questions across 2 subjects,
  multiple chapters/topics/difficulties, including at least a few with LaTeX in the stem.
- **Mechanism:** question modeling & taxonomy.
- **Verify:** query the DB and see varied, well-tagged questions.

### Phase 2 — Read path with caching
- `GET /questions/{id}` fronted by Redis (`q:{id}:v{version}`), with hit/miss + db_query_count
  logging.
- **Mechanism:** the left lane — static content barely touches the DB.
- **Verify:** first fetch = miss + 1 DB query; subsequent fetches = hit + 0 DB queries.

### Phase 3 — Test assembly
- `POST /tests` accepts filters (subject/topic/difficulty/count) → builds and stores an
  ordered `question_ids` list. `GET /tests/{id}` returns the test with cached question payloads.
- **Mechanism:** a test is just an ID list served from cache.
- **Verify:** assembling a test issues few DB queries; fetching it hits cache.

### Phase 4 — Frontend renderer
- React + Vite app: fetch a test, render each question through **one** component switched on
  `type`, with KaTeX for math. Take a test in the browser.
- **Mechanism:** server ships data, client renders.
- **Verify:** MCQ, true/false, and a LaTeX question all render and are answerable.

### Phase 5 — Write path (sync first, then async)
- **5a (sync):** `POST /attempts` records answers and scores them *synchronously*. Note the
  latency.
- **5b (async):** records attempts as unscored, pushes jobs to the Redis queue; a **separate
  worker process** scores them and updates `user_stats`. Compare latency to 5a.
- **Mechanism:** the right lane — decoupling writes from scoring.
- **Verify:** under a burst of submissions, 5b stays fast while the queue drains in the
  background.

### Phase 6 — Analytics + load test
- Worker maintains `user_stats` and a simple leaderboard. Add a k6/Locust script that fires
  many concurrent reads and writes.
- **Mechanism:** everything under pressure — the payoff phase.
- **Verify:** during load, watch `/debug/metrics`: cache hit-rate stays high, question-bank
  DB stays nearly idle, queue depth rises then drains.

### Phase 7 — Offline pack (optional)
- `GET /tests/{id}/pack` returns a self-contained JSON bundle. Take the test "offline",
  then sync attempts on reconnect.
- **Mechanism:** why the static/dynamic split enables offline (ties to nationwide reach).

---

## 9. Working conventions for Claude Code

- **One phase per session.** A focused request ("build Phase 2: the cached read endpoint
  with hit/miss logging") beats "build the backend."
- **Explain as you go.** The goal is the developer *understanding* the mechanisms — annotate
  non-obvious choices and explain tradeoffs, don't just emit code.
- **Always add the instrumentation** specified in the contracts; it is not optional.
- **Keep it runnable.** Every phase ends with a working `docker compose up` and a clear
  manual verification step.
- **Update this file** when an architectural decision changes.
