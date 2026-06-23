import { useState, useEffect } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { useUser } from '@clerk/clerk-react'
import QuestionReview from '../components/QuestionReview.jsx'
import useAuthFetch from '../hooks/useAuthFetch.js'

function buildSelected(type, answer) {
  if (answer == null || answer === '' || (Array.isArray(answer) && answer.length === 0)) return null
  if (type === 'single_mcq' || type === 'true_false') return { id: answer }
  if (type === 'multi_mcq') return { ids: answer }
  if (type === 'numerical') return { value: String(answer) }
  return null
}

function fmtTime(seconds) {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s}s`
  return `${m}m ${String(s).padStart(2, '0')}s`
}

export default function ReviewPage() {
  const { testId } = useParams()
  const { state } = useLocation()
  const navigate = useNavigate()
  const { user } = useUser()
  const authFetch = useAuthFetch()

  const [items, setItems] = useState(null)
  const [score, setScore] = useState(null)
  const [timeTaken, setTimeTaken] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (state?.result && state?.questions) {
      // Came directly from submission — assemble review from router state
      const { result, questions, answers, timeTaken: tt } = state
      const resultMap = Object.fromEntries(result.results.map((r) => [r.question_id, r.is_correct]))
      setItems(
        questions.map((q) => ({
          question_id: q.id,
          question: q,
          selected: buildSelected(q.type, answers[q.id]),
          is_correct: resultMap[q.id] ?? null,
        }))
      )
      setScore(result.score)
      setTimeTaken(tt)
    } else if (user) {
      // Direct URL — fetch from API
      setLoading(true)
      authFetch(`/users/${user.id}/review/${testId}`)
        .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json() })
        .then((data) => {
          setItems(data)
          const correct = data.filter((d) => d.is_correct === true).length
          const total = data.length
          setScore({ correct, total, pct: total ? Math.round((correct / total) * 100) : 0 })
          setLoading(false)
        })
        .catch((e) => { setError(e.message); setLoading(false) })
    }
  }, [testId, state, user])

  if (loading) return <div className="card" style={{ marginTop: '2rem' }}>Loading review…</div>
  if (error) return (
    <div className="card" style={{ marginTop: '2rem' }}>
      <p className="error">{error}</p>
      <button className="secondary" onClick={() => navigate('/')}>Dashboard</button>
    </div>
  )
  if (!items) return null

  return (
    <div>
      {/* Score header */}
      <div className="review-header">
        <div className="score-display">
          <span className="score-number">{score?.correct ?? '?'}/{score?.total ?? '?'}</span>
          <span className="score-pct">{score?.pct ?? 0}%</span>
        </div>
        {timeTaken != null && (
          <div className="time-taken">Time taken: {fmtTime(timeTaken)}</div>
        )}
        <div className="review-header-actions">
          <button className="secondary" onClick={() => navigate('/')}>Back to dashboard</button>
          <button onClick={() => navigate(`/test/${testId}`)}>Retake test</button>
        </div>
      </div>

      {/* Per-question review */}
      <div style={{ marginTop: '1.5rem' }}>
        {items.map((item, i) => (
          item.question ? (
            <QuestionReview
              key={item.question_id}
              index={i}
              question={item.question}
              selected={item.selected}
              is_correct={item.is_correct}
            />
          ) : null
        ))}
      </div>
    </div>
  )
}
