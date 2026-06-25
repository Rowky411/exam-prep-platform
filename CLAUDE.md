# Exam-Prep — Architecture Brief & Build Plan

> Shared source of truth for **what we're building, why, and in what order**.
> Keep it updated as the build progresses.
>
> **Status:** MVP engine complete (Phases 0–6 ✅). Now building the product around the engine.
> Target = **presentable, not production**. A person can sign up, take a test end-to-end on
> their phone, review their answers, see their progress, and you can send the link to someone.

---

## 1. Purpose of this project

Started as a **learning MVP** to make the core mechanisms of a scalable exam-prep platform
visible and touchable. Those mechanisms are now built and load-tested. This stage builds
the **product around the engine**: real accounts, a complete student journey, analytics,
content management, and a design system worth showing.

---

## 2. The one architectural principle that governs everything

Separate **static content** from **dynamic user state**. They have opposite characteristics
and are stored, served, and scaled differently:

- **Questions** — read-heavy, near-immutable, *shared by every user*. Cached at `question_id + version`.
- **Attempts** — write-heavy, *unique per user*. Recorded fast, scored asynchronously.

Reads and writes must never share a hot path.

```
Client
  ├── READ path  → CDN(skipped) → Redis cache → Postgres question bank   [static, shared]
  └── WRITE path → Attempt API  → Redis queue  → worker → attempts/stats  [dynamic, per-user]
```

---

## 3. Guiding principles

1. **Build the architecture, fake the ops.** Localhost Redis teaches the same lesson a CDN does.
2. **Instrument everything.** Cache hit/miss, DB query count, queue depth logged per request.
3. **Vertical slices.** One runnable phase at a time. Verify before moving on.
4. **No premature abstraction.** Smallest thing that demonstrates the mechanism wins.
5. **Static vs dynamic split is sacred.** New read features go through the cache; new writes go through the async path.

---

## 4. Tech stack

| Layer           | Choice                                    | Notes |
|-----------------|-------------------------------------------|-------|
| Backend         | FastAPI (Python 3.11+)                    | One service |
| Source of truth | PostgreSQL                                | `jsonb` for flexible question bodies |
| Cache + queue   | Redis                                     | Cache layer AND the job queue |
| Worker          | Hand-rolled async loop (`worker.py`)      | Separate process from the API |
| Frontend        | React + Vite                              | One question renderer driven by `type` |
| Math render     | KaTeX (client-side)                       | Questions store Markdown + LaTeX, never HTML |
| Orchestration   | Docker Compose                            | `docker compose up` brings up the whole system |
| Load testing    | k6                                        | `docker compose --profile load-test run --rm k6` |
| Auth            | Managed provider (Auth.js / Supabase Auth / Clerk) | Do NOT hand-roll prod auth |
| Charts          | Recharts                                  | For progress / analytics screens |

---

## 5. Deliberate deferrals

- CDN (localhost only for now)
- Elasticsearch / dedicated search index → use Postgres indexes + full-text search
- Cloud infra, autoscaling, Kubernetes
- Anti-piracy, watermarking, payments
- Hosting / deployment → Phase 13, deferred until feature-complete

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
| media         | jsonb     | `[url, ...]` |
| language      | text      | |
| is_active     | bool      | soft delete |
| created_at / updated_at | timestamptz | |

Index on `(subject, chapter, topic, difficulty, exam_tag)` for test assembly.

### `tests`
`id`, `title`, `question_ids jsonb`, `filters jsonb`, `created_at`

### `attempts`
`id`, `user_id`, `test_id`, `question_id`, `question_version`, `selected jsonb`,
`is_correct bool NULL` (null until scored), `submitted_at`, `scored_at NULL`

### `user_stats` (precomputed by the worker)
`user_id`, `total_attempted`, `total_correct`, `accuracy_by_topic jsonb`, `updated_at`

---

## 7. Contracts to honor

**Cache contract.** Key = `q:{id}:v{version}`. On edit, bump `version` → new key written,
stale reads impossible. Reads check Redis first; miss falls through to Postgres and back-fills.

**Async write contract.** On submit: (1) write unscored `attempts` rows, (2) push job to
Redis queue, (3) return fast. Worker scores and updates `user_stats`. API never scores
synchronously in production paths.

**Instrumentation contract.** Logs per request: `cache_hit`/`cache_miss`, `db_query_count`.
Worker logs `queue_depth` + per-job time. `/debug/metrics` dumps live counters.

---

## 8. Design direction (read before any UI work in Phases 9 and 12)

**Subject, audience, job:** exam-prep for students taking high-stakes exams, used heavily on
**low-end Android phones over patchy connections**. One job: let a student take a test and
learn from the result with zero friction. Calm, focused, trustworthy — a study tool, not a game.

**Process before building UI:**
1. Define a compact token system — Color (4–6 hex values), Type (display + body + utility faces),
   Layout concept, one Signature element the product is remembered by.
2. Critique against the brief. Specifically avoid the three AI-default looks:
   (a) cream + high-contrast serif + terracotta; (b) near-black + acid-green/vermilion accent;
   (c) broadsheet hairline-rule columns. If a token reads like a default, revise and note why.

**Non-negotiable quality floor:**
- Mobile-first, responsive to small/low-end screens.
- Visible keyboard focus; respect `prefers-reduced-motion`.
- Every screen has real loading, empty, and error states — never a blank flash.
- Spend boldness in one place (the signature); keep everything else quiet.

**Interface copy rules:**
- Name things by what the user controls. Active voice on actions ("Submit test", not "Submit").
- An action keeps the same name through the whole flow.
- Errors don't apologize and are never vague — say what happened and how to fix it.
- Empty screens invite action ("No tests yet — start with a practice set").

---

## 9. Build phases

### ✅ Phase 0 — Skeleton
Docker Compose with Postgres + Redis; FastAPI boots; `/health` returns 200.

### ✅ Phase 1 — Data model + seed
`questions` schema + seed script (~300 questions, 2 subjects, LaTeX stems).

### ✅ Phase 2 — Read path with caching
`GET /questions/{id}` fronted by Redis (`q:{id}:v{version}`). First fetch = miss + 1 DB query;
subsequent = hit + 0 DB queries.

### ✅ Phase 3 — Test assembly
`POST /tests` (filter → sample → store ID list). `GET /tests/{id}` serves from cache.
Batch Redis lookup: 2 round-trips regardless of question count, 0 DB queries on warm cache.

### ✅ Phase 4 — Frontend renderer
React + Vite. One `QuestionRenderer` component switched on `type`. KaTeX for math.
MCQ (radio), multi-MCQ (checkbox), true/false, numerical all render and are answerable.

### ✅ Phase 5 — Write path (sync + async)
- **5a sync:** `POST /attempts/sync` — scores inline, ~9ms baseline.
- **5b async:** `POST /attempts` — writes unscored rows, pushes to Redis queue, ~4ms.
- Worker (`worker.py`) drains queue, scores, updates `user_stats`.

### ✅ Phase 6 — Analytics + load test
`/leaderboard` endpoint. k6 script: 40 VUs, 90s, 70% reads / 30% writes.
Results: read p95 = 3.99ms, write p95 = 19.46ms, cache hit rate = 99.97%, 0 errors.

---

### Phase 7 — Offline pack (optional, skipped for now)
`GET /tests/{id}/pack` returns a self-contained JSON bundle. Take offline, sync on reconnect.
Mechanism: why the static/dynamic split enables offline.

---

### Phase 8 — Accounts & identity --done
Replace hardcoded `user_id` with real accounts via managed auth provider.
- Signup / login / logout, sessions (JWT or server sessions).
- Two roles: **student** and **admin**. Route guards for each.
- Wire authenticated `user_id` into existing attempts/stats paths.
- **Verify:** two separate accounts each see only their own attempts and stats.

### Phase 9 — The complete student journey --done
Build the full loop. Take-test and review screens are where polish shows.
- **Dashboard:** continue in-progress test, list available tests, recent performance snapshot.
- **Take-test:** countdown timer; question palette (answered / unanswered / flagged);
  next/prev + jump-to-question; flag for review; **autosave answers** (dropped connection
  must never wipe progress — this is the patchy-internet story made real).
- **Results page:** score, time taken, pass/percentile.
- **Answer review:** every question with correct answer, explanation, and student's choice.
  This is the most valuable screen for exam prep — give it real care.
- **Verify:** take a timed test on phone-sized viewport, lose + restore connection mid-test
  without losing answers, submit, and review every answer.

### Phase 10 — Student progress & analytics --done 
Surface the `user_stats` the worker already computes — this is the retention hook.
- Per-topic accuracy, strengths/weaknesses, progress over time, full attempt history.
- A couple of clean Recharts charts. Legible on mobile.
- **Verify:** after several attempts, dashboard reflects accurate per-topic trends.

### Phase 11 — Admin / content management --done
Protected admin area so demos are self-serve instead of raw SQL.
- CRUD for questions; assemble tests; set timers; publish/unpublish.
- Minimal but functional; reuse the design system.
- **Verify:** admin creates a test from UI and a student immediately sees and takes it.

### Phase 12 — Design polish & mobile-first pass
The phase that makes it genuinely presentable.
- Apply the design system coherently across every screen.
- Audit mobile layouts on a real small viewport; fix cramped/broken spots.
- Confirm every loading / empty / error state exists and reads well.
- One restrained signature moment (page-load reveal or a micro-interaction) — not scattered effects.
- **Verify:** walk the whole app on a phone; nothing janky, blank, or templated.

### Phase 13 — Deploy & demo-ready (DEFERRED — hosting not needed yet)
Get it on a public URL.
- Deploy app + managed Postgres + Redis to Railway/Render/Fly.
- Seed demo data and a demo account; env-based config; no secrets in code.
- Basic input validation everywhere; rate-limit auth endpoints.
- **Verify:** open public URL on an unfamiliar phone, sign in with demo account, complete the full loop.

---

## 10. Priority order (if time is tight)

| Priority | Phase | Why |
|----------|-------|-----|
| Must-have | 8 (auth) + 9 (the loop) | Core loop with real accounts *is* the demo |
| Fight to keep | 10 (analytics) | What makes people lean in |
| Can be bare-bones | 11 (admin) | Nice-to-have for self-serve demos |
| Makes it shine | 12 (design polish) | Do as much as time allows |
| Deferred | 13 (deploy) | Until feature-complete |

---

## 11. Working conventions for Claude Code

- **One phase per session.** Focused request beats broad one.
- **Explain non-obvious choices.** Goal is understanding mechanisms, not just shipping code.
- **Always add the instrumentation** specified in the contracts; it is not optional.
- **Keep it runnable.** Every phase ends with a working `docker compose up` and a clear verification step.
- **For UI phases:** show the design token plan before building; update this file when a design or architecture decision changes.
- **Update this file** when an architectural decision changes.
