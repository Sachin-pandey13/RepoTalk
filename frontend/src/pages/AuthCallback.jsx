import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const API = 'http://localhost:8000'

export default function AuthCallback() {
  const nav = useNavigate()
  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(u => nav(u ? '/chat' : '/login'))
      .catch(() => nav('/login'))
  }, [])

  return (
    <div style={{
      height: '100vh', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--obsidian)', gap: 16
    }}>
      <div style={{
        width: 40, height: 40, background: 'var(--indigo)',
        borderRadius: 10, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 16, fontWeight: 700, color: 'white'
      }}>RT</div>
      <div className="spinner" style={{ width: 20, height: 20 }} />
      <p style={{ fontSize: 13, color: 'var(--steel)' }}>Signing you in…</p>
    </div>
  )
}
