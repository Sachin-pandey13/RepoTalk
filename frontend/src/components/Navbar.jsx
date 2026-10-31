import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { User, MessageSquare, Github, LogOut, ChevronDown } from 'lucide-react'

export default function Navbar() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const dropRef = useRef(null)
  const location = useLocation()

  useEffect(() => {
    const handler = (e) => {
      if (dropRef.current && !dropRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : '?'

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-logo">
        <div className="navbar-logo-icon">🧠</div>
        RepoTalk
      </Link>

      <div className="navbar-nav">
        {user && (
          <Link
            to="/chat"
            className={`navbar-link${location.pathname.startsWith('/chat') ? ' active' : ''}`}
          >
            Chat
          </Link>
        )}
        <Link
          to="/"
          className={`navbar-link${location.pathname === '/' ? ' active' : ''}`}
        >
          Home
        </Link>

        {user ? (
          <div className="dropdown" ref={dropRef}>
            <button
              id="profile-avatar-btn"
              className="avatar-btn"
              onClick={() => setOpen(p => !p)}
              title={user.name}
            >
              {user.avatar_url ? (
                <img src={user.avatar_url} alt={user.name} />
              ) : (
                <div className="avatar-initials">{initials}</div>
              )}
            </button>

            {open && (
              <div className="dropdown-menu">
                <div className="dropdown-header">
                  <div className="dropdown-name">{user.name}</div>
                  {user.email && <div className="dropdown-email">{user.email}</div>}
                </div>

                <Link
                  to="/profile"
                  className="dropdown-item"
                  onClick={() => setOpen(false)}
                >
                  <User size={14} />
                  Profile
                </Link>

                <Link
                  to="/chat"
                  className="dropdown-item"
                  onClick={() => setOpen(false)}
                >
                  <MessageSquare size={14} />
                  Chat
                </Link>

                <button
                  className="dropdown-item danger"
                  onClick={() => { logout(); setOpen(false) }}
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </div>
            )}
          </div>
        ) : (
          <Link to="/login" className="btn btn-primary btn-sm">
            Sign in
          </Link>
        )}
      </div>
    </nav>
  )
}
