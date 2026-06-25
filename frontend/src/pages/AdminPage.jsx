import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser } from '@clerk/clerk-react'
import useAuthFetch from '../hooks/useAuthFetch.js'

const TYPES = ['single_mcq', 'multi_mcq', 'true_false', 'numerical']
const EXAM_TAGS = ['HSC', 'admission', 'BCS']
const DIFFICULTIES = [1, 2, 3, 4, 5]

const CORRECT_HINT = {
  single_mcq: '{"id": "a"}',
  multi_mcq: '{"ids": ["a", "b"]}',
  true_false: '{"id": "true"}',
  numerical: '{"value": "42", "tolerance": "0.01"}',
}
const OPTIONS_HINT = '[{"id":"a","text":"..."},{"id":"b","text":"..."}]'

const EMPTY_FORM = {
  type: 'single_mcq', subject: '', chapter: '', topic: '',
  difficulty: 3, exam_tag: 'HSC', stem: '',
  options: '', correct: '', explanation: '', language: 'en',
}

function QuestionForm({ initial, onSave, onCancel, saving }) {
  const [form, setForm] = useState(() => initial
    ? { ...initial, options: initial.options ? JSON.stringify(initial.options, null, 2) : '', correct: JSON.stringify(initial.correct, null, 2) }
    : { ...EMPTY_FORM }
  )
  const [error, setError] = useState('')
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const submit = () => {
    setError('')
    let options = null
    let correct
    try {
      if (form.options.trim()) options = JSON.parse(form.options)
    } catch { return setError('Options: invalid JSON') }
    try {
      correct = JSON.parse(form.correct)
    } catch { return setError('Correct: invalid JSON') }
    if (!form.stem.trim()) return setError('Stem is required')
    onSave({ ...form, options, correct, difficulty: Number(form.difficulty) })
  }

  return (
    <div className="question-form">
      <div className="form-row">
        <label>Type
          <select value={form.type} onChange={(e) => set('type', e.target.value)}>
            {TYPES.map((t) => <option key={t}>{t}</option>)}
          </select>
        </label>
        <label>Subject
          <input value={form.subject} onChange={(e) => set('subject', e.target.value)} placeholder="Physics" />
        </label>
        <label>Chapter
          <input value={form.chapter} onChange={(e) => set('chapter', e.target.value)} placeholder="Mechanics" />
        </label>
        <label>Topic
          <input value={form.topic} onChange={(e) => set('topic', e.target.value)} placeholder="Kinematics" />
        </label>
        <label>Difficulty
          <select value={form.difficulty} onChange={(e) => set('difficulty', e.target.value)}>
            {DIFFICULTIES.map((d) => <option key={d}>{d}</option>)}
          </select>
        </label>
        <label>Exam tag
          <select value={form.exam_tag} onChange={(e) => set('exam_tag', e.target.value)}>
            {EXAM_TAGS.map((t) => <option key={t}>{t}</option>)}
          </select>
        </label>
      </div>

      <label className="field-label">Stem (Markdown + LaTeX)
        <textarea rows={3} value={form.stem} onChange={(e) => set('stem', e.target.value)} placeholder="Question text..." className="admin-textarea" />
      </label>

      <label className="field-label">Options (JSON — omit for numerical)
        <textarea rows={4} value={form.options} onChange={(e) => set('options', e.target.value)} placeholder={OPTIONS_HINT} className="admin-textarea mono" />
      </label>

      <label className="field-label">Correct answer (JSON)
        <textarea rows={2} value={form.correct} onChange={(e) => set('correct', e.target.value)} placeholder={CORRECT_HINT[form.type]} className="admin-textarea mono" />
      </label>

      <label className="field-label">Explanation (optional, Markdown + LaTeX)
        <textarea rows={3} value={form.explanation} onChange={(e) => set('explanation', e.target.value)} placeholder="Explain the answer..." className="admin-textarea" />
      </label>

      {error && <p className="error">{error}</p>}
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
        <button onClick={submit} disabled={saving}>{saving ? 'Saving…' : initial ? 'Update question' : 'Create question'}</button>
        <button className="secondary" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

function QuestionRow({ q, onEdit, onToggle, toggling }) {
  const stem = q.stem.length > 80 ? q.stem.slice(0, 80) + '…' : q.stem
  return (
    <div className={`admin-q-row ${q.is_active ? '' : 'admin-q-inactive'}`}>
      <div className="admin-q-meta">
        <span className="admin-type-badge">{q.type}</span>
        <span className="meta">{q.subject} · {q.topic} · D{q.difficulty}</span>
        <span className={`active-dot ${q.is_active ? 'active-dot-on' : 'active-dot-off'}`}>
          {q.is_active ? 'Published' : 'Unpublished'}
        </span>
      </div>
      <p className="admin-q-stem">{stem}</p>
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
        <button className="secondary icon-btn" onClick={() => onEdit(q)}>Edit</button>
        <button className="secondary icon-btn" onClick={() => onToggle(q.id)} disabled={toggling === q.id}>
          {toggling === q.id ? '…' : q.is_active ? 'Unpublish' : 'Publish'}
        </button>
      </div>
    </div>
  )
}

export default function AdminPage() {
  const navigate = useNavigate()
  const { user } = useUser()
  const authFetch = useAuthFetch()

  const [role, setRole] = useState(null)
  const [overview, setOverview] = useState(null)
  const [questions, setQuestions] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const PER_PAGE = 25

  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState(null)
  const [saving, setSaving] = useState(false)
  const [toggling, setToggling] = useState(null)
  const [error, setError] = useState('')

  const loadQuestions = useCallback(async (p = page) => {
    const r = await authFetch(`/admin/questions?page=${p}&per_page=${PER_PAGE}`)
    if (!r.ok) return
    const data = await r.json()
    setQuestions(data.questions)
    setTotal(data.total)
  }, [authFetch, page])

  useEffect(() => {
    if (!user) return
    authFetch('/me').then((r) => r.json()).then((d) => setRole(d.role)).catch(() => {})
    authFetch('/admin/overview').then((r) => r.json()).then(setOverview).catch(() => {})
    loadQuestions(1)
  }, [user])

  useEffect(() => { loadQuestions(page) }, [page])

  const handleSave = async (formData) => {
    setSaving(true)
    setError('')
    try {
      const url = editing ? `/admin/questions/${editing.id}` : '/admin/questions'
      const method = editing ? 'PUT' : 'POST'
      const r = await authFetch(url, { method, body: JSON.stringify(formData) })
      if (!r.ok) {
        const d = await r.json()
        throw new Error(d.detail ?? r.statusText)
      }
      setCreating(false)
      setEditing(null)
      await loadQuestions(page)
      const ov = await authFetch('/admin/overview').then((r) => r.json())
      setOverview(ov)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (id) => {
    setToggling(id)
    try {
      await authFetch(`/admin/questions/${id}/toggle`, { method: 'PATCH' })
      await loadQuestions(page)
    } finally {
      setToggling(null)
    }
  }

  if (role === null) return <p className="loading-msg">Loading…</p>
  if (role !== 'admin') {
    return (
      <div style={{ textAlign: 'center', paddingTop: '4rem' }}>
        <p style={{ color: '#dc2626', fontWeight: 600 }}>Admin access required.</p>
        <button className="secondary" style={{ marginTop: '1rem' }} onClick={() => navigate('/')}>Back to dashboard</button>
      </div>
    )
  }

  const totalPages = Math.ceil(total / PER_PAGE)

  return (
    <div>
      <header className="app-header">
        <button className="secondary icon-btn" onClick={() => navigate('/')}>← Back</button>
        <h1 style={{ margin: 0, flex: 1 }}>Admin</h1>
      </header>

      {overview && (
        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value">{overview.questions}</div>
            <div className="stat-label">Questions</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{overview.active_questions}</div>
            <div className="stat-label">Published</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{overview.tests}</div>
            <div className="stat-label">Tests</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{overview.users}</div>
            <div className="stat-label">Users</div>
          </div>
        </div>
      )}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0 }}>Questions</h2>
          {!creating && !editing && (
            <button onClick={() => setCreating(true)}>+ New question</button>
          )}
        </div>

        {(creating || editing) && (
          <QuestionForm
            initial={editing}
            onSave={handleSave}
            onCancel={() => { setCreating(false); setEditing(null); setError('') }}
            saving={saving}
          />
        )}
        {error && <p className="error">{error}</p>}

        {!creating && !editing && (
          <>
            <div className="admin-q-list">
              {questions.length === 0 && <p className="empty-state">No questions yet.</p>}
              {questions.map((q) => (
                <QuestionRow
                  key={q.id}
                  q={q}
                  onEdit={(q) => { setEditing(q); setCreating(false) }}
                  onToggle={handleToggle}
                  toggling={toggling}
                />
              ))}
            </div>
            {totalPages > 1 && (
              <div className="pagination">
                <button className="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Prev</button>
                <span className="meta">Page {page} of {totalPages}</span>
                <button className="secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next →</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
