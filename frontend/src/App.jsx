import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, SignIn, SignUp } from '@clerk/clerk-react'
import Dashboard from './pages/Dashboard.jsx'
import TakeTest from './pages/TakeTest.jsx'
import ReviewPage from './pages/ReviewPage.jsx'

function AuthScreen() {
  const [mode, setMode] = useState('signin')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: '3rem' }}>
      <h1 style={{ marginBottom: '1.5rem' }}>Exam Prep</h1>
      {mode === 'signin' ? <SignIn routing="hash" /> : <SignUp routing="hash" />}
      <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#6b7280' }}>
        {mode === 'signin'
          ? <><span>No account? </span><button className="link-btn" onClick={() => setMode('signup')}>Create one</button></>
          : <><span>Already have an account? </span><button className="link-btn" onClick={() => setMode('signin')}>Sign in</button></>
        }
      </p>
    </div>
  )
}

export default function App() {
  return (
    <>
      <SignedIn>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/test/:testId" element={<TakeTest />} />
          <Route path="/review/:testId" element={<ReviewPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </SignedIn>
      <SignedOut>
        <AuthScreen />
      </SignedOut>
    </>
  )
}
