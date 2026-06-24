import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUser } from '@clerk/clerk-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import useAuthFetch from '../hooks/useAuthFetch.js'

function TopicChart({ data }) {
  if (!data.length) {
    return <p className="empty-state">No topic data yet — take some tests first.</p>
  }
  const height = Math.max(data.length * 44, 120)
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart layout="vertical" data={data} margin={{ top: 4, right: 48, bottom: 4, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="topic" width={130} tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v) => [`${v}%`, 'Accuracy']} />
        <Bar dataKey="accuracy" radius={[0, 4, 4, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.accuracy >= 70 ? '#16a34a' : entry.accuracy >= 45 ? '#2563eb' : '#dc2626'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function StrengthsWeaknesses({ data }) {
  if (data.length < 2) return null
  const sorted = [...data].sort((a, b) => b.accuracy - a.accuracy)
  const strong = sorted.slice(0, 3)
  const weak = [...data].sort((a, b) => a.accuracy - b.accuracy).slice(0, 3)
  return (
    <div className="sw-grid">
      <div>
        <h3 className="sw-heading sw-strong-heading">Strong topics</h3>
        {strong.map((t) => (
          <div key={t.topic} className="sw-item sw-strong">
            <span className="sw-topic">{t.topic}</span>
            <span className="sw-pct">{t.accuracy}%</span>
          </div>
        ))}
      </div>
      <div>
        <h3 className="sw-heading sw-weak-heading">Needs work</h3>
        {weak.map((t) => (
          <div key={t.topic} className="sw-item sw-weak">
            <span className="sw-topic">{t.topic}</span>
            <span className="sw-pct">{t.accuracy}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function AttemptHistory({ history }) {
  if (!history.length) {
    return <p className="empty-state">No completed tests yet.</p>
  }
  return (
    <div className="history-list">
      {history.map((h) => (
        <div key={h.test_id} className="history-row">
          <div>
            <div className="test-title">{h.title}</div>
            <div className="meta">
              {h.correct}/{h.total} correct
              {h.submitted_at ? ` · ${new Date(h.submitted_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}` : ''}
            </div>
          </div>
          <span className={`score-badge ${h.score_pct >= 70 ? 'score-pass' : h.score_pct >= 45 ? 'score-mid' : 'score-fail'}`}>
            {h.score_pct}%
          </span>
        </div>
      ))}
    </div>
  )
}

export default function ProgressPage() {
  const navigate = useNavigate()
  const { user } = useUser()
  const authFetch = useAuthFetch()
  const [stats, setStats] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) return
    Promise.all([
      authFetch(`/users/${user.id}/stats`).then((r) => r.json()),
      authFetch(`/users/${user.id}/attempts/history`).then((r) => r.json()),
    ])
      .then(([s, h]) => { setStats(s); setHistory(h) })
      .catch(() => setError('Failed to load progress data.'))
      .finally(() => setLoading(false))
  }, [user])

  const topicData = stats?.accuracy_by_topic
    ? Object.entries(stats.accuracy_by_topic)
        .map(([topic, d]) => ({
          topic,
          accuracy: Math.round((d.correct / Math.max(d.attempted, 1)) * 100),
          attempted: d.attempted,
        }))
        .sort((a, b) => b.attempted - a.attempted)
    : []

  return (
    <div>
      <header className="app-header">
        <button className="secondary icon-btn" onClick={() => navigate('/')} style={{ marginRight: '0.5rem' }}>
          ← Back
        </button>
        <h1 style={{ margin: 0, flex: 1 }}>Your Progress</h1>
      </header>

      {loading && <p className="loading-msg">Loading…</p>}
      {error && <p className="error">{error}</p>}

      {!loading && stats && (
        <>
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
              <div className="stat-value">{stats.total_attempted > 0 ? `${stats.accuracy}%` : '—'}</div>
              <div className="stat-label">Accuracy</div>
            </div>
          </div>

          {topicData.length >= 2 && (
            <div className="card">
              <h2>Strengths & Weaknesses</h2>
              <StrengthsWeaknesses data={topicData} />
            </div>
          )}

          <div className="card">
            <h2>Accuracy by Topic</h2>
            <TopicChart data={topicData} />
          </div>

          <div className="card">
            <h2>Recent Tests</h2>
            <AttemptHistory history={history} />
          </div>
        </>
      )}

      {!loading && !stats && !error && (
        <div className="empty-state" style={{ paddingTop: '4rem' }}>
          <p>No data yet — take a test to see your progress here.</p>
        </div>
      )}
    </div>
  )
}
