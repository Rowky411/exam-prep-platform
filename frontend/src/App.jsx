import { useState } from 'react'
import {
  SignedIn,
  SignedOut,
  SignIn,
  SignUp,
  UserButton,
  useAuth,
  useUser,
} from '@clerk/clerk-react'
import QuestionRenderer from './QuestionRenderer.jsx'

const SUBJECTS = ['Physics', 'Mathematics']
const EXAM_TAGS = ['HSC', 'admission', 'BCS']

function buildSelected(type, answer) {
  if (answer == null || answer === '' || (Array.isArray(answer) && answer.length === 0)) return null
  if (type === 'single_mcq' || type === 'true_false') return { id: answer }
  if (type === 'multi_mcq') return { ids: answer }
  if (type === 'numerical') return { value: String(answer) }
  return null
}

function useAuthFetch() {
  const { getToken } = useAuth()
  return async (url, options = {}) => {
    const token = await getToken()
    return fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    })
  }
}

// ---------------------------------------------------------------------------
// Assembly form
// ---------------------------------------------------------------------------
function AssemblyForm({ onTest, loading }) {
  const authFetch = useAuthFetch()
  const [form, setForm] = useState({ subject: 'Physics', exam_tag: '', difficulty: '', count: 10, title: '' })
  const [loadId, setLoadId] = useState('')
  const [error, setError] = useState('')
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const assemble = async () => {
    setError('')
    const body = { count: Number(form.count) }
    if (form.subject)    body.subject   = form.subject
    if (form.exam_tag)   body.exam_tag  = form.exam_tag
    if (form.difficulty) body.difficulty = Number(form.difficulty)
    if (form.title)      body.title     = form.title
    try {
      const res = await fetch('/tests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
      const test = await res.json()
      onTest(test.id)
    } catch (e) { setError(e.message) }
  }

  const load = async () => {
    setError('')
    if (!loadId.trim()) return
    onTest(loadId.trim())
  }

  return (
    <div className="card">
      <h2>Assemble a Test</h2>
      <div className="form-row">
        <label>Subject
          <select value={form.subject} onChange={(e) => set('subject', e.target.value)}>
            <option value="">Any</option>
            {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label>Exam Tag
          <select value={form.exam_tag} onChange={(e) => set('exam_tag', e.target.value)}>
            <option value="">Any</option>
            {EXAM_TAGS.map((t) => <option key={t}>{t}</option>)}
          </select>
        </label>
        <label>Difficulty
          <select value={form.difficulty} onChange={(e) => set('difficulty', e.target.value)}>
            <option value="">Any</option>
            {[1,2,3,4,5].map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>
        <label>Count
          <input type="number" min={1} max={50} value={form.count} onChange={(e) => set('count', e.target.value)} />
        </label>
        <label>Title (optional)
          <input type="text" placeholder="My Test" value={form.title} onChange={(e) => set('title', e.target.value)} />
        </label>
      </div>
      <button onClick={assemble} disabled={loading}>{loading ? 'Loading…' : 'Assemble Test'}</button>
      {error && <p className="error">{error}</p>}

      <hr style={{ margin: '1.25rem 0', borderColor: '#e5e7eb' }} />
      <h2>Load by Test ID</h2>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input type="text" placeholder="paste test UUID…" value={loadId} onChange={(e) => setLoadId(e.target.value)}
          style={{ flex: 1, padding: '0.4rem 0.6rem', border: '1px solid #ccc', borderRadius: '4px' }} />
        <button onClick={load} disabled={loading} className="secondary">Load</button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Result screen
// ---------------------------------------------------------------------------
function ResultScreen({ result, onBack }) {
  const { user } = useUser()
  const authFetch = useAuthFetch()
  const [stats, setStats] = useState(null)

  const fetchStats = async () => {
    const res = await authFetch(`/users/${user.id}/stats`)
    setStats(await res.json())
  }

  return (
    <div>
      <div className="result-box">
        {result.mode === 'sync' ? (
          <>
            <h2>Score: {result.score.correct}/{result.score.total} ({result.score.pct}%)</h2>
            <p>Answered and scored synchronously in <strong>{result.elapsed_ms} ms</strong>.</p>
          </>
        ) : (
          <>
            <h2>{result.queued} answers queued</h2>
            <p>
              Submitted in <strong>{result.elapsed_ms} ms</strong> — scoring happens in the background.
              Queue depth after submit: <strong>{result.queue_depth}</strong>.
            </p>
          </>
        )}
      </div>

      {result.mode === 'async' && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <p style={{ marginBottom: '0.75rem', fontSize: '0.9rem', color: '#555' }}>
            Worker is draining the queue. Check stats once it finishes:
          </p>
          <button onClick={fetchStats} className="secondary">Fetch my stats</button>
          {stats && (
            <pre style={{ marginTop: '0.75rem', fontSize: '0.8rem', background: '#f3f4f6', padding: '0.75rem', borderRadius: '4px', overflowX: 'auto' }}>
              {JSON.stringify(stats, null, 2)}
            </pre>
          )}
        </div>
      )}

      <div className="submit-row" style={{ marginTop: '1rem' }}>
        <button className="secondary" onClick={onBack}>New Test</button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Test view
// ---------------------------------------------------------------------------
function TestView({ testId, onBack }) {
  const authFetch = useAuthFetch()
  const [test, setTest] = useState(null)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  useState(() => {
    fetch(`/tests/${testId}`)
      .then((r) => { if (!r.ok) throw new Error(`Test not found (${r.status})`); return r.json() })
      .then((data) => { setTest(data); setLoading(false) })
      .catch((e) => { setError(e.message); setLoading(false) })
  })

  if (loading) return <div className="card">Loading test…</div>
  if (error)   return <div className="card"><p className="error">{error}</p><button className="secondary" onClick={onBack}>Back</button></div>
  if (!test)   return null
  if (result)  return <ResultScreen result={result} onBack={onBack} />

  const answered = Object.keys(answers).length
  const total = test.questions.length
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0

  const submit = async (mode) => {
    setSubmitting(true)
    setError('')

    const answers_payload = test.questions
      .map((q) => {
        const sel = buildSelected(q.type, answers[q.id])
        if (!sel) return null
        return { question_id: q.id, question_version: q.version, selected: sel }
      })
      .filter(Boolean)

    if (answers_payload.length === 0) {
      setError('Answer at least one question first.')
      setSubmitting(false)
      return
    }

    const endpoint = mode === 'sync' ? '/attempts/sync' : '/attempts'
    try {
      const res = await authFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify({ test_id: testId, answers: answers_payload }),
      })
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h1>{test.title}</h1>
          <div className="meta">{total} questions · {answered} answered</div>
        </div>
        <button className="secondary" onClick={onBack}>← Back</button>
      </div>

      <div className="progress-bar">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>

      {test.questions.map((q, i) => (
        <QuestionRenderer
          key={q.id}
          index={i}
          question={q}
          answer={answers[q.id]}
          onChange={(val) => setAnswers((a) => ({ ...a, [q.id]: val }))}
        />
      ))}

      {error && <p className="error" style={{ marginBottom: '0.5rem' }}>{error}</p>}

      <div className="submit-row">
        <button className="secondary" onClick={onBack} disabled={submitting}>← Back</button>
        <button className="secondary" onClick={() => submit('sync')} disabled={submitting} title="Score synchronously — baseline latency">
          {submitting ? '…' : 'Submit (sync)'}
        </button>
        <button onClick={() => submit('async')} disabled={submitting} title="Enqueue for background scoring — fast response">
          {submitting ? 'Submitting…' : 'Submit (async)'}
        </button>
      </div>
      <p style={{ textAlign: 'right', fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.4rem' }}>
        sync = scores inline · async = queues for worker
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Auth screen (shown when signed out)
// ---------------------------------------------------------------------------
function AuthScreen() {
  const [mode, setMode] = useState('signin')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '3rem' }}>
      <h1 style={{ marginBottom: '1.5rem' }}>Exam Prep</h1>
      {mode === 'signin'
        ? <SignIn routing="hash" />
        : <SignUp routing="hash" />
      }
      <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#6b7280' }}>
        {mode === 'signin'
          ? <><span>No account? </span><button className="link-btn" onClick={() => setMode('signup')}>Create one</button></>
          : <><span>Already have an account? </span><button className="link-btn" onClick={() => setMode('signin')}>Sign in</button></>
        }
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main app (shown when signed in)
// ---------------------------------------------------------------------------
function MainApp() {
  const { user } = useUser()
  const [testId, setTestId] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleTest = (id) => { setLoading(true); setTestId(id); setLoading(false) }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0 }}>Exam Prep</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>{user?.primaryEmailAddress?.emailAddress}</span>
          <UserButton afterSignOutUrl="/" />
        </div>
      </div>
      {!testId
        ? <AssemblyForm onTest={handleTest} loading={loading} />
        : <TestView testId={testId} onBack={() => setTestId(null)} />
      }
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root
// ---------------------------------------------------------------------------
export default function App() {
  return (
    <>
      <SignedIn>
        <MainApp />
      </SignedIn>
      <SignedOut>
        <AuthScreen />
      </SignedOut>
    </>
  )
}
