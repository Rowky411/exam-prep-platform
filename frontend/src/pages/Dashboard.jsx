import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { UserButton, useUser } from '@clerk/clerk-react'
import useAuthFetch from '../hooks/useAuthFetch.js'

const SUBJECTS = ['Physics', 'Mathematics']
const EXAM_TAGS = ['HSC', 'admission', 'BCS']

function StatsSnapshot({ stats }) {
  if (!stats) return null
  const acc = stats.total_attempted > 0
    ? Math.round((stats.total_correct / stats.total_attempted) * 100)
    : null
  return (
    <div className="stats-row">
      <div className="stat-card">
        <div className="stat-value">{stats.total_attempted}</div>
        <div className="stat-label">Attempted</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{stats.total_correct}</div>
        <div className="stat-label">Correct</div>
      </div>
      <div className="stat-card">
        <div className="stat-value">{acc !== null ? `${acc}%` : '—'}</div>
        <div className="stat-label">Accuracy</div>
      </div>
    </div>
  )
}

function TestList({ tests, inProgress, navigate }) {
  if (tests.length === 0) {
    return (
      <div className="empty-state">
        <p>No tests yet — create one below to get started.</p>
      </div>
    )
  }
  return (
    <div className="test-list">
      {inProgress && (
        <div className="in-progress-banner">
          <span>In-progress test found</span>
          <button onClick={() => navigate(`/test/${inProgress.testId}`)}>Continue</button>
        </div>
      )}
      {tests.map((t) => (
        <div key={t.id} className="test-row">
          <div>
            <div className="test-title">{t.title}</div>
            <div className="meta">
              {t.question_count} questions
              {t.duration_minutes ? ` · ${t.duration_minutes} min` : ' · Untimed'}
              {t.filters?.subject ? ` · ${t.filters.subject}` : ''}
            </div>
          </div>
          <button onClick={() => navigate(`/test/${t.id}`)}>Take test</button>
        </div>
      ))}
    </div>
  )
}

function AssemblyForm({ onCreated, loading, setLoading }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ subject: 'Physics', exam_tag: '', difficulty: '', count: 10, title: '', duration_minutes: '' })
  const [error, setError] = useState('')
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const assemble = async () => {
    setError('')
    setLoading(true)
    const body = { count: Number(form.count) }
    if (form.subject)          body.subject = form.subject
    if (form.exam_tag)         body.exam_tag = form.exam_tag
    if (form.difficulty)       body.difficulty = Number(form.difficulty)
    if (form.title)            body.title = form.title
    if (form.duration_minutes) body.duration_minutes = Number(form.duration_minutes)
    try {
      const res = await fetch('/tests', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
      const test = await res.json()
      setOpen(false)
      onCreated(test.id)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>Create a test</h2>
        <button className="secondary" onClick={() => setOpen((v) => !v)}>
          {open ? 'Cancel' : '+ New test'}
        </button>
      </div>
      {open && (
        <div style={{ marginTop: '1rem' }}>
          <div className="form-row">
            <label>Subject
              <select value={form.subject} onChange={(e) => set('subject', e.target.value)}>
                <option value="">Any</option>
                {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </label>
            <label>Exam tag
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
            <label>Questions
              <input type="number" min={1} max={50} value={form.count} onChange={(e) => set('count', e.target.value)} />
            </label>
            <label>Time limit (min)
              <input type="number" min={1} max={180} placeholder="Untimed" value={form.duration_minutes} onChange={(e) => set('duration_minutes', e.target.value)} />
            </label>
            <label>Title
              <input type="text" placeholder="Practice set" value={form.title} onChange={(e) => set('title', e.target.value)} />
            </label>
          </div>
          <button onClick={assemble} disabled={loading}>{loading ? 'Creating…' : 'Create & take test'}</button>
          {error && <p className="error">{error}</p>}
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useUser()
  const authFetch = useAuthFetch()
  const [tests, setTests] = useState([])
  const [stats, setStats] = useState(null)
  const [role, setRole] = useState(null)
  const [loading, setLoading] = useState(false)
  const [inProgress, setInProgress] = useState(null)

  useEffect(() => {
    fetch('/tests').then((r) => r.json()).then(setTests).catch(() => {})
    if (user) {
      authFetch(`/users/${user.id}/stats`).then((r) => r.json()).then(setStats).catch(() => {})
      authFetch('/users/me').then((r) => r.json()).then((d) => setRole(d.role)).catch(() => {})
    }
  }, [user])

  // Check for in-progress draft in localStorage
  useEffect(() => {
    if (!user) return
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key && key.startsWith(`examprep:draft:${user.id}:`)) {
        const testId = key.split(':')[3]
        if (testId) { setInProgress({ testId }); break }
      }
    }
  }, [user])

  const handleCreated = (testId) => navigate(`/test/${testId}`)

  return (
    <div>
      <header className="app-header">
        <h1>Exam Prep</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span className="email-label">{user?.primaryEmailAddress?.emailAddress}</span>
          <button className="secondary" style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }} onClick={() => navigate('/progress')}>Progress</button>
          {role === 'admin' && (
            <button className="secondary" style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }} onClick={() => navigate('/admin')}>Admin</button>
          )}
          <UserButton afterSignOutUrl="/" />
        </div>
      </header>

      {stats && <StatsSnapshot stats={stats} />}

      <div className="card">
        <h2>Tests</h2>
        <TestList tests={tests} inProgress={inProgress} navigate={navigate} />
      </div>

      <AssemblyForm onCreated={handleCreated} loading={loading} setLoading={setLoading} />
    </div>
  )
}
