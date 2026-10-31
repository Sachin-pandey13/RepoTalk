import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * Handles the OAuth redirect callback.
 * The backend sets httpOnly cookies and redirects to /auth/callback.
 * This page simply triggers a refetch of /auth/me and navigates to /chat.
 */
export default function AuthCallback() {
  const { refetch } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const handleCallback = async () => {
      await refetch()
      const pending = sessionStorage.getItem('pending_repo')
      if (pending) {
        sessionStorage.removeItem('pending_repo')
        navigate(`/chat?repo=${encodeURIComponent(pending)}`, { replace: true })
      } else {
        navigate('/chat', { replace: true })
      }
    }
    handleCallback()
  }, [refetch, navigate])

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: '1rem',
      }}
    >
      <div className="spinner" style={{ width: 48, height: 48, borderWidth: 4 }} />
      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
        Completing sign-in…
      </p>
    </div>
  )
}
