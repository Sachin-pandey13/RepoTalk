import { Github, Mail, Zap } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { user, loading, loginWithGithub, loginWithGoogle } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading && user) {
      navigate('/chat', { replace: true })
    }
  }, [user, loading, navigate])

  if (loading) return null

  return (
    <div className="auth-page">
      {/* Background orbs */}
      <div className="hero-orb hero-orb-1" style={{ opacity: 0.35 }} />
      <div className="hero-orb hero-orb-2" style={{ opacity: 0.25 }} />

      <div className="auth-card glass-card animate-fade-in-up">
        {/* Logo */}
        <div className="auth-logo">
          <span style={{ fontSize: '2rem' }}>🧠</span>
          <span className="gradient-text" style={{ fontSize: '1.5rem', fontWeight: 700 }}>RepoTalk</span>
        </div>

        <h1 className="auth-title">Welcome back</h1>
        <p className="auth-subtitle">
          Sign in to start exploring repositories with AI‑powered Q&amp;A
        </p>

        {/* OAuth Buttons */}
        <div className="auth-buttons">
          <button
            id="github-login-btn"
            className="auth-btn auth-btn-github"
            onClick={loginWithGithub}
          >
            <Github size={18} />
            Continue with GitHub
          </button>

          <button
            id="google-login-btn"
            className="auth-btn auth-btn-google"
            onClick={loginWithGoogle}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
              <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
        </div>

        <div className="auth-divider">
          <span />
          <p>Secure OAuth — we never store your password</p>
          <span />
        </div>

        <div className="auth-features">
          {[
            { icon: '🔒', text: 'httpOnly cookie sessions — no token exposure' },
            { icon: '⚡', text: 'Instant repo ingestion with vector search' },
            { icon: '🛡️', text: 'Rate‑limited, header‑secured API' },
          ].map((f, i) => (
            <div key={i} className="auth-feature-row">
              <span>{f.icon}</span>
              <span>{f.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
