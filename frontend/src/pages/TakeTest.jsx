import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useUser } from '@clerk/clerk-react'
import QuestionRenderer from '../QuestionRenderer.jsx'
import QuestionPalette from '../components/QuestionPalette.jsx'
import Timer from '../components/Timer.jsx'
import useAuthFetch from '../hooks/useAuthFetch.js'

function buildSelected(type, answer) {
  if (answer == null || answer === '' || (Array.isArray(answer) && answer.length === 0)) return null
  if (type === 'single_mcq' || type === 'true_false') return { id: answer }
  if (type === 'multi_mcq') return { ids: answer }
  if (type === 'numerical') return { value: String(answer) }
  return null
}

function draftKey(userId, testId) {
  return `examprep:draft:${userId}:${testId}`
}

function fmtTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s}s`
  return `${m}m ${s}s`
}

export default function TakeTest() {
  const { testId } = useParams()
  const navigate = useNavigate()
  const { user } = useUser()
  const authFetch = useAuthFetch()

  const [test, setTest] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState({})
  const [flagged, setFlagged] = useState(new Set())
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)
  const startedAtRef = useRef(null)

  // Load test
  useEffect(() => {
    fetch(`/tests/${testId}`)
      .then((r) => { if (!r.ok) throw new Error(`Test not found (${r.status})`); return r.json() })
      .then((data) => { setTest(data); setLoading(false) })
      .catch((e) => { setError(e.message); setLoading(false) })
  }, [testId])

  // Restore or init draft after test + user both ready
  useEffect(() => {
    if (!test || !user) return
    const saved = localStorage.getItem(draftKey(user.id, testId))
    if (saved) {
      try {
        const draft = JSON.parse(saved)
        setAnswers(draft.answers ?? {})
        setFlagged(new Set(draft.flagged ?? []))
        startedAtRef.current = new Date(draft.startedAt)
        return
      } catch { /* bad data, fall through */ }
    }
    startedAtRef.current = new Date()
  }, [test, user, testId])

  // Autosave draft whenever answers or flagged changes
  useEffect(() => {
    if (!test || !user || !startedAtRef.current) return
    const draft = {
      answers,
      flagged: Array.from(flagged),
      startedAt: startedAtRef.current.toISOString(),
      savedAt: new Date().toISOString(),
    }
    localStorage.setItem(draftKey(user.id, testId), JSON.stringify(draft))
  }, [answers, flagged, test, user, testId])

  const handleAnswer = (qid, val) => setAnswers((a) => ({ ...a, [qid]: val }))

  const toggleFlag = () => {
    const qid = test.questions[currentIdx].id
    setFlagged((f) => {
      const next = new Set(f)
      next.has(qid) ? next.delete(qid) : next.add(qid)
      return next
    })
  }

  const doSubmit = useCallback(async () => {
    if (!test || !user) return
    setSubmitting(true)
    setSubmitError('')
    setShowConfirm(false)

    const answers_payload = test.questions
      .map((q) => {
        const sel = buildSelected(q.type, answers[q.id])
        if (!sel) return null
        return { question_id: q.id, question_version: q.version, selected: sel }
      })
      .filter(Boolean)

    if (answers_payload.length === 0) {
      setSubmitError('Answer at least one question.')
      setSubmitting(false)
      return
    }

    const timeTaken = Math.round((Date.now() - startedAtRef.current.getTime()) / 1000)

    try {
      const res = await authFetch('/attempts/sync', {
        method: 'POST',
        body: JSON.stringify({ test_id: testId, answers: answers_payload }),
      })
      if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText)
      const result = await res.json()
      localStorage.removeItem(draftKey(user.id, testId))
      navigate(`/review/${testId}`, {
        state: { result, questions: test.questions, answers, timeTaken },
      })
    } catch (e) {
      setSubmitError(e.message)
      setSubmitting(false)
    }
  }, [test, user, testId, answers, authFetch, navigate])

  const handleSubmitClick = () => {
    const unanswered = test.questions.filter((q) => !answers[q.id]).length
    if (unanswered > 0) {
      setShowConfirm(true)
    } else {
      doSubmit()
    }
  }

  if (loading) return <div className="card" style={{ marginTop: '2rem' }}>Loading test…</div>
  if (error) return (
    <div className="card" style={{ marginTop: '2rem' }}>
      <p className="error">{error}</p>
      <button className="secondary" onClick={() => navigate('/')}>Back to dashboard</button>
    </div>
  )
  if (!test) return null

  const q = test.questions[currentIdx]
  const answeredSet = new Set(
    test.questions.map((_, i) => i).filter((i) => {
      const qid = test.questions[i].id
      const a = answers[qid]
      return a != null && a !== '' && !(Array.isArray(a) && a.length === 0)
    })
  )
  const flaggedSet = new Set(
    test.questions.map((_, i) => i).filter((i) => flagged.has(test.questions[i].id))
  )

  const unansweredCount = test.questions.length - answeredSet.size

  return (
    <div className="take-test-layout">
      {/* Header */}
      <div className="test-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 }}>
          <button className="secondary icon-btn" onClick={() => navigate('/')} title="Back to dashboard">←</button>
          <h1 className="test-header-title">{test.title}</h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexShrink: 0 }}>
          {test.duration_minutes && startedAtRef.current && (
            <Timer
              totalSeconds={test.duration_minutes * 60}
              onExpire={doSubmit}
            />
          )}
          <button onClick={handleSubmitClick} disabled={submitting}>
            {submitting ? 'Submitting…' : 'Submit test'}
          </button>
        </div>
      </div>

      {/* Palette */}
      <QuestionPalette
        count={test.questions.length}
        answeredSet={answeredSet}
        flaggedSet={flaggedSet}
        currentIdx={currentIdx}
        onJump={setCurrentIdx}
      />

      {/* Question */}
      <div className="question-area">
        <QuestionRenderer
          index={currentIdx}
          question={q}
          answer={answers[q.id]}
          onChange={(val) => handleAnswer(q.id, val)}
        />

        {submitError && <p className="error">{submitError}</p>}

        {/* Nav */}
        <div className="question-nav">
          <button
            className="secondary"
            onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
            disabled={currentIdx === 0}
          >
            ← Previous
          </button>
          <button
            className={`flag-btn${flagged.has(q.id) ? ' flagged' : ''}`}
            onClick={toggleFlag}
          >
            {flagged.has(q.id) ? '⚑ Flagged' : '⚐ Flag for review'}
          </button>
          <button
            className="secondary"
            onClick={() => setCurrentIdx((i) => Math.min(test.questions.length - 1, i + 1))}
            disabled={currentIdx === test.questions.length - 1}
          >
            Next →
          </button>
        </div>
      </div>

      {/* Submit confirmation modal */}
      {showConfirm && (
        <div className="modal-backdrop">
          <div className="modal">
            <h2>Submit test?</h2>
            <p>
              {unansweredCount} question{unansweredCount !== 1 ? 's' : ''} unanswered.
              You can still go back and answer them.
            </p>
            <div className="modal-actions">
              <button className="secondary" onClick={() => setShowConfirm(false)}>Go back</button>
              <button onClick={doSubmit}>Submit anyway</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
