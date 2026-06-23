import { useState } from 'react'
import QuestionRenderer from './QuestionRenderer.jsx'

const SUBJECTS = ['Physics', 'Mathematics']
const EXAM_TAGS = ['HSC', 'admission', 'BCS']

function AssemblyForm({ onTest, loading }) {
  const [form, setForm] = useState({
    subject: 'Physics',
    exam_tag: '',
    difficulty: '',
    count: 10,
    title: '',
  })
  const [loadId, setLoadId] = useState('')
  const [error, setError] = useState('')

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const assemble = async () => {
    setError('')
    const body = { count: Number(form.count) }
    if (form.subject) body.subject = form.subject
    if (form.exam_tag) body.exam_tag = form.exam_tag
    if (form.difficulty) body.difficulty = Number(form.difficulty)
    if (form.title) body.title = form.title
    try {
      const res = await fetch('/tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const d = await res.json()
        throw new Error(d.detail ?? res.statusText)
      }
      const test = await res.json()
      onTest(test.id)
    } catch (e) {
      setError(e.message)
    }
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
        <label>
          Subject
          <select value={form.subject} onChange={(e) => set('subject', e.target.value)}>
            <option value="">Any</option>
            {SUBJECTS.map((s) => <option key={s}>{s}</option>)}
          </select>
        </label>
        <label>
          Exam Tag
          <select value={form.exam_tag} onChange={(e) => set('exam_tag', e.target.value)}>
            <option value="">Any</option>
            {EXAM_TAGS.map((t) => <option key={t}>{t}</option>)}
          </select>
        </label>
        <label>
          Difficulty
          <select value={form.difficulty} onChange={(e) => set('difficulty', e.target.value)}>
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>
        <label>
          Count
          <input
            type="number"
            min={1}
            max={50}
            value={form.count}
            onChange={(e) => set('count', e.target.value)}
          />
        </label>
        <label>
          Title (optional)
          <input
            type="text"
            placeholder="My Test"
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
          />
        </label>
      </div>
      <button onClick={assemble} disabled={loading}>
        {loading ? 'Loading…' : 'Assemble Test'}
      </button>
      {error && <p className="error">{error}</p>}

      <hr style={{ margin: '1.25rem 0', borderColor: '#e5e7eb' }} />
      <h2>Load by Test ID</h2>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          type="text"
          placeholder="paste test UUID…"
          value={loadId}
          onChange={(e) => setLoadId(e.target.value)}
          style={{ flex: 1, padding: '0.4rem 0.6rem', border: '1px solid #ccc', borderRadius: '4px' }}
        />
        <button onClick={load} disabled={loading} className="secondary">Load</button>
      </div>
    </div>
  )
}

function TestView({ testId, onBack }) {
  const [test, setTest] = useState(null)
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)

  // Fetch test on mount
  useState(() => {
    fetch(`/tests/${testId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Test not found (${r.status})`)
        return r.json()
      })
      .then((data) => { setTest(data); setLoading(false) })
      .catch((e) => { setError(e.message); setLoading(false) })
  })

  if (loading) return <div className="card">Loading test…</div>
  if (error) return <div className="card"><p className="error">{error}</p><button className="secondary" onClick={onBack}>Back</button></div>
  if (!test) return null

  const answered = Object.keys(answers).length
  const total = test.questions.length
  const pct = total > 0 ? Math.round((answered / total) * 100) : 0

  const setAnswer = (qid, val) => setAnswers((a) => ({ ...a, [qid]: val }))

  const submit = () => {
    // Phase 5 will POST to /attempts. For now just show summary.
    setSubmitted(true)
  }

  if (submitted) {
    return (
      <div>
        <div className="result-box">
          <h2>Answers Recorded</h2>
          <p>You answered {answered} of {total} questions.</p>
          <p style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#6b7280' }}>
            Scoring wired up in Phase 5.
          </p>
        </div>
        <div className="submit-row">
          <button className="secondary" onClick={onBack}>New Test</button>
        </div>
      </div>
    )
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
          onChange={(val) => setAnswer(q.id, val)}
        />
      ))}

      <div className="submit-row">
        <button className="secondary" onClick={onBack}>← Back</button>
        <button onClick={submit}>Submit Answers</button>
      </div>
    </div>
  )
}

export default function App() {
  const [testId, setTestId] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleTest = (id) => {
    setLoading(true)
    setTestId(id)
    setLoading(false)
  }

  const handleBack = () => setTestId(null)

  return (
    <div>
      <h1>Exam Prep</h1>
      {!testId
        ? <AssemblyForm onTest={handleTest} loading={loading} />
        : <TestView testId={testId} onBack={handleBack} />
      }
    </div>
  )
}
