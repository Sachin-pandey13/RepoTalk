import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Github, Mail, Calendar, Star, GitBranch, LogOut, RefreshCw } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function StatCard({ icon, label, value, color }) {
  return (
    <div className="stat-card glass-card">
      <div className={`stat-icon stat-icon--${color}`}>{icon}</div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  )
}

export default function Profile() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const [repos, setRepos] = useState([])
  const [repoLoading, setRepoLoading] = useState(true)

  useEffect(() => {
    if (!loading && !user) navigate('/login', { replace: true })
  }, [user, loading, navigate])

  useEffect(() => {
    if (!user) return
    const load = async () => {
      try {
        const resp = await fetch(`${API}/chat/repos`, { credentials: 'include' })
        if (resp.ok) {
          const data = await resp.json()
          setRepos(data.repos || [])
        }
      } catch {}
      setRepoLoading(false)
    }
    load()
  }, [user])

  const handleLogout = async () => {
    await logout()
    navigate('/', { replace: true })
  }

  if (loading || !user) return null

  const initials = user.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : '?'

  const joinedDate = user.created_at
    ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
    : 'N/A'

  return (
    <div className="profile-page">
      <div className="profile-bg" />

      <div className="container container--narrow" style={{ position: 'relative', zIndex: 1 }}>
        {/* Profile card */}
        <div className="profile-card glass-card animate-fade-in-up">
          <div className="profile-avatar-wrap">
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.name}
                className="profile-avatar"
              />
            ) : (
              <div className="profile-avatar profile-avatar--initials">
                {initials}
              </div>
            )}
            <div className="profile-provider-badge">
              {user.provider === 'github' ? <Github size={14} /> : '🔵'}
            </div>
          </div>

          <div className="profile-info">
            <h1 className="profile-name">{user.name}</h1>
            {user.email && (
              <div className="profile-detail">
                <Mail size={13} />
                {user.email}
              </div>
            )}
            {user.github_username && (
              <div className="profile-detail">
                <Github size={13} />
                <a
                  href={`https://github.com/${user.github_username}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  @{user.github_username}
                </a>
              </div>
            )}
            <div className="profile-detail">
              <Calendar size={13} />
              Member since {joinedDate}
            </div>
          </div>

          <button
            id="logout-btn"
            className="btn btn-ghost btn-sm"
            style={{ marginTop: '1rem', alignSelf: 'flex-start' }}
            onClick={handleLogout}
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>

        {/* Stats */}
        <div className="stats-grid animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <StatCard
            icon={<GitBranch size={18} />}
            label="Repositories Indexed"
            value={repos.length}
            color="violet"
          />
          <StatCard
            icon={'🧠'}
            label="Provider"
            value={user.provider === 'github' ? 'GitHub' : 'Google'}
            color="mint"
          />
          <StatCard
            icon={'🔒'}
            label="Session"
            value="Secure"
            color="amber"
          />
        </div>

        {/* Indexed repos */}
        <div className="glass-card animate-fade-in-up" style={{ animationDelay: '0.2s', marginTop: '1.5rem', padding: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>
              <GitBranch size={15} style={{ display: 'inline', marginRight: '0.4rem', color: 'var(--violet-400)' }} />
              Indexed Repositories
            </h2>
          </div>

          {repoLoading && (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: 'var(--text-muted)' }}>
              <div className="spinner" style={{ width: 16, height: 16 }} />
              Loading…
            </div>
          )}

          {!repoLoading && repos.length === 0 && (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '1rem 0' }}>
              No repositories indexed yet. Head to the{' '}
              <a onClick={() => navigate('/chat')} style={{ cursor: 'pointer', color: 'var(--violet-400)' }}>
                Chat page
              </a>{' '}
              to add one.
            </div>
          )}

          <div className="profile-repos">
            {repos.map((r, i) => (
              <div
                key={i}
                className="profile-repo-item"
                onClick={() => navigate(`/chat?repo=${encodeURIComponent(r)}`)}
              >
                <GitBranch size={14} />
                <span>{r}</span>
                <span className="profile-repo-chat">Chat →</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
