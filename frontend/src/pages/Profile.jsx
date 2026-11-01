import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, GitBranch, MessageSquare, LogOut, User, Mail, Shield } from 'lucide-react'

const API = 'http://localhost:8000'

export default function Profile() {
  const nav = useNavigate()
  const [user, setUser]   = useState(null)
  const [repos, setRepos] = useState([])

  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(u => { if (u) setUser(u); else nav('/login') })
      .catch(() => nav('/login'))

    fetch(`${API}/chat/repos`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(d => d?.repos && setRepos(d.repos))
      .catch(() => {})
  }, [])

  const logout = async () => {
    await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' })
    nav('/login')
  }

  if (!user) return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="spinner" style={{ width: 24, height: 24 }} />
    </div>
  )

  const initial = (user.name || user.username || 'U')[0].toUpperCase()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--obsidian)', padding: '32px 24px' }}>
      <div style={{ maxWidth: 680, margin: '0 auto' }}>

        {/* Back */}
        <button
          className="btn btn-ghost btn-sm flex items-center gap-2"
          onClick={() => nav('/chat')}
          style={{ marginBottom: 24 }}
        >
          <ArrowLeft size={13} /> Back to dashboard
        </button>

        {/* Profile card */}
        <motion.div
          className="card"
          style={{ padding: 28, marginBottom: 16, border: '1px solid var(--border-bright)' }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <div style={{
              width: 68, height: 68, borderRadius: '50%',
              background: 'var(--indigo)', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              fontSize: 26, fontWeight: 700, color: 'white', flexShrink: 0,
              overflow: 'hidden', border: '2px solid var(--indigo)44'
            }}>
              {user.avatar_url
                ? <img src={user.avatar_url} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                : initial}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--cloud)', marginBottom: 4 }}>
                {user.name || user.username}
              </div>
              {user.email && (
                <div style={{ fontSize: 13, color: 'var(--steel)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Mail size={12} /> {user.email}
                </div>
              )}
              <div style={{ marginTop: 10 }}>
                <span className="badge badge-indigo" style={{ textTransform: 'capitalize' }}>
                  <Shield size={10} /> {user.provider}
                </span>
              </div>
            </div>
            <button className="btn btn-secondary btn-sm flex items-center gap-2" onClick={logout}>
              <LogOut size={12} /> Sign out
            </button>
          </div>
        </motion.div>

        {/* Stats */}
        <motion.div
          style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          {[
            { label: 'Repositories', value: repos.length, color: 'var(--indigo)', icon: <GitBranch size={16}/> },
            { label: 'Provider', value: user.provider, color: 'var(--ice)', icon: <User size={16}/> },
            { label: 'Status', value: 'Active', color: 'var(--mint)', icon: <Shield size={16}/> },
          ].map((s, i) => (
            <div key={i} className="card" style={{ textAlign: 'center', padding: '20px 16px' }}>
              <div style={{ color: s.color, display: 'flex', justifyContent: 'center', marginBottom: 8 }}>{s.icon}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--cloud)', marginBottom: 2, textTransform: 'capitalize' }}>
                {s.value}
              </div>
              <div style={{ fontSize: 12, color: 'var(--steel)' }}>{s.label}</div>
            </div>
          ))}
        </motion.div>

        {/* Repo list */}
        {repos.length > 0 && (
          <motion.div
            className="card"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18 }}
          >
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--cloud)', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
              <GitBranch size={14} style={{ color: 'var(--indigo)' }} />
              Indexed Repositories
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {repos.map(r => (
                <div
                  key={r}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '10px 12px', borderRadius: 'var(--radius)',
                    background: 'var(--slate)', cursor: 'pointer',
                    border: '1px solid transparent', transition: 'all 0.12s'
                  }}
                  onClick={() => nav('/chat')}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--indigo)33'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'transparent'}
                >
                  <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--mint)', boxShadow: '0 0 6px var(--mint)88', flexShrink: 0 }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--cloud)', flex: 1 }}>{r}</span>
                  <span style={{ fontSize: 11, color: 'var(--mint)' }}>Ready</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
