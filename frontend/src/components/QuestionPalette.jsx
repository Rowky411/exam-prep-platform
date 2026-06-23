export default function QuestionPalette({ count, answeredSet, flaggedSet, currentIdx, onJump }) {
  return (
    <nav className="palette" aria-label="Question palette">
      {Array.from({ length: count }, (_, i) => {
        const state = flaggedSet.has(i)
          ? 'flagged'
          : answeredSet.has(i)
          ? 'answered'
          : 'unanswered'
        return (
          <button
            key={i}
            className={`palette-btn palette-${state}${i === currentIdx ? ' palette-current' : ''}`}
            onClick={() => onJump(i)}
            aria-label={`Question ${i + 1}${flaggedSet.has(i) ? ', flagged' : ''}`}
            aria-current={i === currentIdx ? 'true' : undefined}
          >
            {i + 1}
          </button>
        )
      })}
    </nav>
  )
}
