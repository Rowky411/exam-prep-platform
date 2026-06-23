import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

function Stem({ text }) {
  return (
    <div className="stem">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {text}
      </ReactMarkdown>
    </div>
  )
}

const DIFF_LABELS = ['', 'Easy', 'Easy-Med', 'Medium', 'Med-Hard', 'Hard']

export default function QuestionRenderer({ index, question, answer, onChange }) {
  const { type, stem, options, subject, topic, difficulty, exam_tag } = question

  const isSelected = (id) =>
    type === 'multi_mcq'
      ? Array.isArray(answer) && answer.includes(id)
      : answer === id

  const handleMulti = (id, checked) => {
    const current = Array.isArray(answer) ? answer : []
    onChange(checked ? [...current, id] : current.filter((v) => v !== id))
  }

  return (
    <div className="question-card">
      <div className="question-number">Question {index + 1}</div>
      <div className="meta">
        <span className="tag">{subject}</span>
        <span className="tag">{exam_tag}</span>
        {topic && <span className="tag">{topic}</span>}
        <span className="difficulty-badge">{DIFF_LABELS[difficulty] ?? difficulty}</span>
      </div>

      <Stem text={stem} />

      {/* single choice */}
      {(type === 'single_mcq' || type === 'true_false') && (
        <div className="options">
          {options.map((opt) => (
            <label key={opt.id} className={isSelected(opt.id) ? 'selected' : ''}>
              <input
                type="radio"
                name={question.id}
                value={opt.id}
                checked={isSelected(opt.id)}
                onChange={() => onChange(opt.id)}
              />
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{ p: ({ children }) => <span>{children}</span> }}
              >
                {opt.text}
              </ReactMarkdown>
            </label>
          ))}
        </div>
      )}

      {/* multiple choice */}
      {type === 'multi_mcq' && (
        <div className="options">
          {options.map((opt) => (
            <label key={opt.id} className={isSelected(opt.id) ? 'selected' : ''}>
              <input
                type="checkbox"
                value={opt.id}
                checked={isSelected(opt.id)}
                onChange={(e) => handleMulti(opt.id, e.target.checked)}
              />
              <ReactMarkdown
                remarkPlugins={[remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{ p: ({ children }) => <span>{children}</span> }}
              >
                {opt.text}
              </ReactMarkdown>
            </label>
          ))}
        </div>
      )}

      {/* numerical */}
      {type === 'numerical' && (
        <div className="numerical-input">
          <input
            type="number"
            placeholder="Enter numeric answer"
            value={answer ?? ''}
            onChange={(e) => onChange(e.target.value)}
          />
        </div>
      )}
    </div>
  )
}
