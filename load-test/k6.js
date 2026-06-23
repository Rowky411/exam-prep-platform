/**
 * Phase 6 load test — fires mixed reads + writes against the API.
 *
 * What to watch during the run:
 *   Terminal A (this script):  k6 live stats — req/s, p95 latency, error rate
 *   Terminal B:  watch -n1 "curl -s http://localhost:8000/debug/metrics | python -m json.tool"
 *
 * Expected behaviour:
 *   - Read p95 stays well under 50ms (questions served from Redis, 0 DB queries)
 *   - Write p95 stays under 200ms (queue push, no scoring inline)
 *   - redis_hit_rate climbs toward 1.0 as cache warms
 *   - queue_depth rises during the burst then drains to 0 after ramp-down
 *   - Postgres is nearly idle on the question-bank side
 */

import http from 'k6/http'
import { check, sleep } from 'k6'

const BASE = __ENV.BASE_URL || 'http://api:8000'

export const options = {
  stages: [
    { duration: '20s', target: 40 },  // ramp up
    { duration: '60s', target: 40 },  // hold — main observation window
    { duration: '10s', target: 0  },  // ramp down
  ],
  thresholds: {
    'http_req_duration{endpoint:read}':  ['p(95)<200'],
    'http_req_duration{endpoint:write}': ['p(95)<400'],
    'http_req_failed': ['rate<0.01'],
  },
}

// ---------------------------------------------------------------------------
// setup() runs once before VUs start — pre-warm two tests in the cache
// ---------------------------------------------------------------------------
export function setup() {
  const tests = []

  for (const subject of ['Physics', 'Mathematics']) {
    const createRes = http.post(
      `${BASE}/tests`,
      JSON.stringify({ subject, count: 10, title: `Load Test — ${subject}` }),
      { headers: { 'Content-Type': 'application/json' } },
    )
    check(createRes, { 'test created (201)': (r) => r.status === 201 })

    // Fetch the test once to warm question payloads into Redis
    const fetchRes = http.get(`${BASE}/tests/${createRes.json('id')}`)
    check(fetchRes, { 'test fetched (200)': (r) => r.status === 200 })

    tests.push(fetchRes.json())
  }

  return { tests }
}

// ---------------------------------------------------------------------------
// default() runs for every VU on every iteration
// ---------------------------------------------------------------------------
export default function (data) {
  const test = data.tests[Math.floor(Math.random() * data.tests.length)]

  if (Math.random() < 0.7) {
    // ── READ PATH (70%) ────────────────────────────────────────────────────
    // After setup() the cache is warm — these should be 0 DB queries each.
    const res = http.get(`${BASE}/tests/${test.id}`, {
      tags: { endpoint: 'read' },
    })
    check(res, { 'read 200': (r) => r.status === 200 })

  } else {
    // ── WRITE PATH (30%) ───────────────────────────────────────────────────
    // Submit 5 random answers async — should return quickly regardless of
    // how many writes are in-flight. Worker drains the queue separately.
    const answers = test.questions.slice(0, 5).map((q) => {
      let selected
      if (q.type === 'single_mcq' || q.type === 'true_false') {
        selected = { id: q.options[Math.floor(Math.random() * q.options.length)].id }
      } else if (q.type === 'multi_mcq') {
        selected = { ids: [q.options[0].id] }
      } else {
        selected = { value: String((Math.random() * 100).toFixed(2)) }
      }
      return { question_id: q.id, question_version: q.version, selected }
    })

    const res = http.post(
      `${BASE}/attempts`,
      JSON.stringify({ user_id: `vu${__VU}`, test_id: test.id, answers }),
      { headers: { 'Content-Type': 'application/json' }, tags: { endpoint: 'write' } },
    )
    check(res, { 'write 202': (r) => r.status === 202 })
  }

  sleep(0.05 + Math.random() * 0.25)
}

// ---------------------------------------------------------------------------
// teardown() runs once after all VUs finish — snapshot final state
// ---------------------------------------------------------------------------
export function teardown() {
  const metrics  = http.get(`${BASE}/debug/metrics`).json()
  const board    = http.get(`${BASE}/leaderboard`).json()

  console.log('\n=== Final Cache Metrics ===')
  console.log(`  hit rate:     ${metrics.redis_hit_rate}`)
  console.log(`  hits:         ${metrics.redis_keyspace_hits}`)
  console.log(`  misses:       ${metrics.redis_keyspace_misses}`)
  console.log(`  queue depth:  ${metrics.queue_depth}  (0 = fully drained)`)

  console.log('\n=== Leaderboard (top 5) ===')
  board.slice(0, 5).forEach((u) =>
    console.log(`  #${u.rank} ${u.user_id}  ${u.total_correct}/${u.total_attempted} (${u.accuracy}%)`)
  )
}
