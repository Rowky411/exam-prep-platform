# Exam Prep Platform

A scalable exam-prep platform built to demonstrate architectural patterns: static/dynamic content separation, Redis caching, async write queues, and a full student journey from sign-up to answer review.

## Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL 16 |
| Cache + Queue | Redis 7 |
| Worker | Async Python process (`worker.py`) |
| Frontend | React 18 + Vite |
| Auth | Clerk |
| Charts | Recharts |
| Math | KaTeX |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A [Clerk](https://clerk.com) account (free tier is enough)

## Setup

### 1. Clone & enter the repo

```bash
git clone <repo-url>
cd exam-prep-platform
```

### 2. Configure environment variables

**Backend (root `.env`):**

```bash
cp .env.example .env
```

Edit `.env` and set your Clerk JWKS URL:

```
CLERK_JWKS_URL=https://your-app.clerk.accounts.dev/.well-known/jwks.json
```

Find it: Clerk Dashboard → your app → API Keys → Advanced → JWT verification endpoint.

**Frontend (`frontend/.env.local`):**

```bash
cp frontend/.env.local.example frontend/.env.local
```

Edit `frontend/.env.local` and set your Clerk publishable key:

```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

Find it: Clerk Dashboard → your app → API Keys.

### 3. Start the system

```bash
docker compose up
```

This starts:
- PostgreSQL on port `5432`
- Redis on port `6379`
- FastAPI API on port `8000`
- Async worker (queue drainer)
- React frontend on port `5173`

First run builds the Docker images — takes a few minutes.

### 4. Seed the database

In a separate terminal, once the API is healthy:

```bash
docker compose exec api python scripts/seed.py
```

Seeds ~300 questions across 2 subjects with LaTeX math stems.

### 5. Open the app

```
http://localhost:5173
```

Sign up, take a test, review answers, check progress.

---

## Architecture

```
Client
  ├── READ path  → Redis cache → PostgreSQL question bank   [static, shared]
  └── WRITE path → Attempt API → Redis queue → worker       [dynamic, per-user]
```

**Cache key:** `q:{id}:v{version}` — version bumped on edit, stale reads impossible.

**Write flow:** submit → write unscored attempt row → push to Redis queue → return fast. Worker scores asynchronously and updates `user_stats`.

## API

Base URL: `http://localhost:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/questions/{id}` | GET | Fetch question (cached) |
| `/tests` | POST | Assemble test from filters |
| `/tests/{id}` | GET | Fetch test (cached) |
| `/attempts` | POST | Submit answers (async) |
| `/me/stats` | GET | Authenticated user stats |
| `/me/attempts` | GET | Attempt history |
| `/leaderboard` | GET | Top scores |
| `/debug/metrics` | GET | Live cache/queue counters |
| `/admin/*` | * | Admin CRUD (admin role required) |

## Load Testing

```bash
docker compose --profile load-test run --rm k6
```

40 virtual users, 90s, 70% reads / 30% writes.
Baseline results: read p95 = 3.99ms, write p95 = 19.46ms, cache hit rate = 99.97%.

## Project Structure

```
exam-prep-platform/
├── backend/
│   ├── app/
│   │   ├── main.py       # FastAPI app, routes
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── auth.py       # Clerk JWT verification
│   │   └── db.py         # DB connection
│   ├── scripts/
│   │   └── seed.py       # Question seeder
│   ├── worker.py         # Async queue worker
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/        # Dashboard, TakeTest, Review, Progress, Admin
│   │   ├── components/   # QuestionPalette, Timer, QuestionReview
│   │   ├── hooks/        # useAuthFetch
│   │   ├── App.jsx       # Routes
│   │   └── main.jsx      # Entry point
│   └── package.json
├── load-test/
│   └── k6.js
├── docker-compose.yml
└── .env.example
```

## Roles

- **Student** — sign up, take tests, review answers, view progress
- **Admin** — create/edit questions, assemble tests, publish/unpublish (set in Clerk dashboard metadata: `role: "admin"`)

## Stopping

```bash
docker compose down
```

To also wipe the database volume:

```bash
docker compose down -v
```
