import { useState, useEffect, useRef } from 'react'

export default function Timer({ totalSeconds, onExpire }) {
  const [remaining, setRemaining] = useState(totalSeconds)
  const expiredRef = useRef(false)

  useEffect(() => {
    if (remaining <= 0) {
      if (!expiredRef.current) {
        expiredRef.current = true
        onExpire()
      }
      return
    }
    const id = setTimeout(() => setRemaining((r) => r - 1), 1000)
    return () => clearTimeout(id)
  }, [remaining, onExpire])

  const m = Math.floor(remaining / 60)
  const s = remaining % 60
  const urgent = remaining <= 60

  return (
    <span
      className={`timer${urgent ? ' timer-urgent' : ''}`}
      aria-label={`${m} minutes ${s} seconds remaining`}
    >
      {String(m).padStart(2, '0')}:{String(s).padStart(2, '0')}
    </span>
  )
}
