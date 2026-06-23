import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

function MD({ children }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
      {children}
    </ReactMarkdown>
  )
}

function MDInline({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{ p: ({ children }) => <span>{children}</span> }}
    >
      {children}
    </ReactMarkdown>
  )
}

const DIFF_LABELS = ['', 'Easy', 'Easy-Med', 'Medium', 'Med-Hard', 'Hard']

export default function QuestionReview({ index, question, selected, is_correct }) {
  const { type, stem, options, correct, explanation, subject, topic, difficulty, exam_tag } = question

  const userSelectedId = selected?.id
  const userSelectedIds = new Set(selected?.ids ?? [])
  const correctId = correct?.id
  const correctIds = new Set(correct?.ids ?? [])

  const optionState = (id) => {
    const isCorrect = type === 'multi_mcq' ? correctIds.has(id) : id === correctId
    const isSelected = type === 'multi_mcq' ? userSelectedIds.has(id) : id === userSelectedId
    if (isSelected && isCorrect) return 'opt-correct'
    if (isSelected && !isCorrect) return 'opt-wrong'
    if (!isSelected && isCorrect) return 'opt-missed'
    return ''
  }

  return (
    <div className={`question-card review-card${is_correct ? ' review-correct' : is_correct === false ? ' review-wrong' : ''}`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="question-number">Question {index + 1}</div>
        <span className={`result-badge ${is_correct ? 'result-correct' : is_correct === false ? 'result-wrong' : 'result-pending'}`}>
          {is_correct === true ? '✓ Correct' : is_correct === false ? '✗ Wrong' : '— Pending'}
        </span>
      </div>

      <div className="meta">
        <span className="tag">{subject}</span>
        <span className="tag">{exam_tag}</span>
        {topic && <span className="tag">{topic}</span>}
        <span className="difficulty-badge">{DIFF_LABELS[difficulty] ?? difficulty}</span>
      </div>

      <div className="stem"><MD>{stem}</MD></div>

      {/* MCQ / true-false options */}
      {(type === 'single_mcq' || type === 'true_false' || type === 'multi_mcq') && options && (
        <div className="options">
          {options.map((opt) => (
            <div key={opt.id} className={`review-option ${optionState(opt.id)}`}>
              <MDInline>{opt.text}</MDInline>
            </div>
          ))}
        </div>
      )}

      {/* Numerical */}
      {type === 'numerical' && (
        <div className="numerical-review">
          <div>Your answer: <strong>{selected?.value ?? '—'}</strong></div>
          <div>Correct: <strong>{correct?.value}</strong>{correct?.tolerance ? ` ± ${correct.tolerance}` : ''}</div>
        </div>
      )}

      {/* Explanation */}
      {explanation && (
        <div className="explanation">
          <div className="explanation-label">Explanation</div>
          <MD>{explanation}</MD>
        </div>
      )}
    </div>
  )
}
