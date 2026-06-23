# Exam-Prep — Build Plan: Productization (Phases 8–13)

> Continuation of the MVP `CLAUDE.md`. The MVP proved the **engine** (the static/dynamic
> split, caching, async writes). This stage builds the **product around the engine**: a real
> multi-user app with a complete, polished journey, deployed to a public URL.
>
> Target = **presentable, not production**. A person can sign up, take a test end-to-end on
> their phone, review their answers, see their progress, and you can send the link to someone.
> We are **not** doing the question content in this stage — focus is the surrounding product.

---

## Carried-over principles (still apply)

1. **Build the architecture, fake the ops** — managed services over hand-rolled infra.
2. **Vertical slices** — one runnable phase at a time; verify before moving on; commit after each.
3. **Static vs dynamic split is sacred** — new read features go through the cache; new writes
   go through the async path.
4. **Instrument it** — keep the hit/miss + query-count logging working as the app grows.

---

## Stack additions for this stage

| Need            | Choice                                              | Notes |
|-----------------|-----------------------------------------------------|-------|
| Auth            | A managed provider (Auth.js / Supabase Auth / Clerk)| Do **not** hand-roll prod auth |
| Charts          | Recharts (or Chart.js)                              | For the progress screens |
| Hosting         | Railway / Render / Fly.io                           | Managed Postgres + Redis alongside |
| Config          | `.env` based, no secrets in code                    | One config path for local + deployed |

---

## Design direction & system (READ BEFORE ANY UI WORK)

The UI is what makes this "presentable," so it must not look templated. Before writing
component code in Phases 9 and 12, **produce a small design token system first** and follow it.

**Subject, audience, job (the brief):** a focused exam-prep test platform for students
preparing for high-stakes exams, used heavily on **low-end Android phones over patchy
connections**. The page's one job: let a student take a test and learn from the result with
zero friction. Calm, focused, trustworthy — this is a study tool, not a game.

**Do the two-pass process from the design skill:**
1. Define a compact token system — **Color** (4–6 named hex values), **Type** (a characterful
   display face used with restraint + a clean body face + a utility face for data/labels),
   **Layout** concept, and one **Signature** element the product is remembered by.
2. Critique it against the brief before building. Specifically **avoid the three AI-default
   looks**: (a) cream background + high-contrast serif + terracotta accent; (b) near-black +
   single acid-green/vermilion accent; (c) broadsheet hairline-rule columns. If a token reads
   like a default rather than a choice for *this* exam-prep brief, revise it and note why.

**Non-negotiable quality floor** (build to it without announcing it):
- **Mobile-first**, responsive down to small/low-end screens — this audience is the reason.
- Visible keyboard focus; respect `prefers-reduced-motion`.
- Every screen has real **loading, empty, and error** states — never a blank flash.
- Spend boldness in one place (the signature); keep everything else quiet and disciplined.

**Interface copy is design material:**
- Name things by what the user controls, in plain terms. Active voice on actions
  ("Submit test", not "Submit"; the button that says "Publish" yields a toast "Published").
- An action keeps the same name through the whole flow.
- Errors don't apologize and are never vague — say what happened and how to fix it.
- Empty screens invite action ("No tests yet — start with a practice set").

---

## Build phases

Each phase is independently runnable. Finish + verify + commit before the next.

### Phase 8 — Accounts & identity
Replace the hardcoded `user_id` with real accounts.
- Signup / login / logout, sessions (JWT or server sessions), via the managed provider.
- Two roles: **student** and **admin**. Route guards for each.
- Wire the real authenticated `user_id` into the existing attempts/stats paths.
- **Verify:** two separate accounts each see only their own attempts and stats.

### Phase 9 — The complete student journey (the heart of "presentable")
Build the full loop. The **take-test** and **review** screens are where polish shows.
- **Dashboard / home:** continue an in-progress test, list available tests, a snapshot of
  recent performance.
- **Take-test experience:** countdown timer for timed tests; a **question palette**
  (answered / unanswered / flagged); next / previous + jump-to-question; **flag for review**;
  **autosave of answers** so a dropped connection never wipes progress (demo this — it's the
  nationwide/patchy-internet story made real).
- **Results page:** score, time taken, pass/percentile.
- **Answer review:** every question with the correct answer, the explanation, and the
  student's choice. For exam prep this is the most valuable screen — give it real care.
- **Verify:** take a timed test on a phone-sized viewport, lose and restore the connection
  mid-test without losing answers, submit, and review every answer.

### Phase 10 — Student progress & analytics
Surface the `user_stats` the worker already computes — this is the retention hook.
- Per-topic accuracy, strengths/weaknesses, progress over time, full attempt history.
- A couple of clean charts (Recharts). Keep them legible on mobile.
- **Verify:** after several attempts, the dashboard reflects accurate per-topic trends.

### Phase 11 — Admin / content management
A protected admin area so demos are self-serve instead of raw SQL. (Content itself stays out
of scope — this is the *management surface*.)
- CRUD for questions; assemble tests; set timers; publish / unpublish.
- Minimal but functional; reuse the design system.
- **Verify:** an admin creates a test from the UI and a student immediately sees and takes it.

### Phase 12 — Design polish & mobile-first pass
The phase that makes it genuinely presentable.
- Apply the design system coherently across every screen.
- Audit mobile layouts on a real small viewport; fix cramped/broken spots.
- Confirm every loading / empty / error state exists and reads well.
- One restrained signature moment (a page-load reveal or a hover/scroll micro-interaction) —
  not scattered effects.
- **Verify:** walk the whole app on a phone; nothing janky, blank, or templated.

### Phase 13 — Deploy & demo-ready
Get it on a public URL you can send.
- Deploy app + managed Postgres + Redis to Railway/Render/Fly.
- Seed **demo data** and a **demo account**; env-based config; no secrets in code.
- Basic input validation everywhere; rate-limit the auth endpoints.
- **Verify:** open the public URL on a phone you've never used, sign in with the demo account,
  complete the full loop.

---

## If time is tight — priority order

- **Must-have for a demo:** Phase 8 (auth) + Phase 9 (the loop, especially take-test →
  review) + Phase 13 (deploy). The core loop on a real URL with real accounts *is* the demo.
- **Fight to keep:** Phase 10 (analytics) — it's what makes people lean in.
- **Can be bare-bones:** Phase 11 (admin).
- **Makes it shine:** Phase 12 (design polish) — do as much as time allows.

---

## Working conventions for Claude Code (unchanged)

- One phase per session; a focused request beats a broad one.
- Explain non-obvious choices and tradeoffs — the goal is understanding.
- Keep the instrumentation working as features land.
- Every phase ends runnable with a clear manual verification step.
- For UI phases, **show the design token plan before building**, and update this file when a
  design or architecture decision changes.
