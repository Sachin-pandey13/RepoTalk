import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useState } from 'react'
import { ArrowRight, Github, Zap, Search, GitBranch, Brain, MessageSquare, Code2 } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const FEATURES = [
  {
    icon: '🧠',
    color: 'violet',
    title: 'Autonomous RAG Agent',
    desc: 'Multi-step reasoning agent investigates your repo with semantic search, AST analysis, and call-graph traversal to deliver evidence-backed answers.',
  },
  {
    icon: '🌳',
    color: 'mint',
    title: 'Deep Code Parsing',
    desc: 'Tree-sitter AST parsing extracts every function, class, import, and call chain — across all languages in your repository.',
  },
  {
    icon: '🔍',
    color: 'amber',
    title: 'Vector Semantic Search',
    desc: 'ChromaDB-powered embeddings let you search by meaning, not just keywords. Find related code across hundreds of files instantly.',
  },
  {
    icon: '💬',
    color: 'violet',
    title: 'Natural Language Q&A',
    desc: 'Ask anything: "How does auth work?", "What calls parse_file?", "Walk me through the request lifecycle" — get cited, structured answers.',
  },
  {
    icon: '📊',
    color: 'mint',
    title: 'Dependency Graphs',
    desc: 'Visualise module import chains and function call flows as interactive diagrams. Understand your codebase architecture at a glance.',
  },
  {
    icon: '🔐',
    color: 'amber',
    title: 'Secure by Design',
    desc: 'OAuth via GitHub & Google. JWT sessions in httpOnly cookies. Rate limiting. Path traversal protection. Your repos stay private.',
  },
]

const EXAMPLE_QUESTIONS = [
  'How does the auth middleware work?',
  'What calls the parse_file function?',
  'Explain the RAG pipeline end to end',
  'How do I run this project locally?',
  'What are the main data models?',
  'Walk me through a request lifecycle',
]

export default function Landing() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)

  const handleTryNow = async () => {
    if (!repoUrl.trim()) return
    if (!user) {
      // Save url and redirect to login
      sessionStorage.setItem('pending_repo', repoUrl)
      navigate('/login')
      return
    }
    setLoading(true)
    try {
      const resp = await fetch(`${API}/chat/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ repo_url: repoUrl }),
      })
      if (resp.ok) {
        const data = await resp.json()
        navigate(`/chat?repo=${encodeURIComponent(data.repo_name)}`)
      }
    } catch {}
    setLoading(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleTryNow()
  }

  return (
    <div className="landing">
      {/* Hero */}
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-orb hero-orb-1" />
        <div className="hero-orb hero-orb-2" />
        <div className="hero-orb hero-orb-3" />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <div className="hero-badge animate-fade-in-up">
            <span className="hero-badge-dot" />
            Powered by RAG + AST Intelligence
          </div>

          <h1 className="hero-title animate-fade-in-up delay-100">
            Understand Any{' '}
            <span className="gradient-text">GitHub Repo</span>
            <br />
            Instantly
          </h1>

          <p className="hero-subtitle animate-fade-in-up delay-200">
            Paste a repository link and ask anything. RepoTalk parses, indexes,
            and reasons over the entire codebase — explaining every file,
            function, and architectural decision.
          </p>

          <div className="hero-url-demo animate-fade-in-up delay-300">
            <Code2 size={16} color="var(--text-muted)" />
            <input
              id="hero-repo-input"
              value={repoUrl}
              onChange={e => setRepoUrl(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="https://github.com/owner/repo"
            />
            <button
              id="hero-try-btn"
              className="btn btn-primary btn-sm"
              onClick={handleTryNow}
              disabled={loading || !repoUrl.trim()}
            >
              {loading ? '…' : 'Analyse'}
              {!loading && <ArrowRight size={14} />}
            </button>
          </div>

          <div className="hero-actions animate-fade-in-up delay-400">
            {user ? (
              <Link to="/chat" className="btn btn-primary btn-lg" id="go-to-chat-btn">
                Open Chat
                <ArrowRight size={16} />
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn btn-primary btn-lg" id="landing-signin-btn">
                  <Github size={18} />
                  Sign in with GitHub
                </Link>
                <Link to="/login" className="btn btn-ghost btn-lg">
                  Learn more
                </Link>
              </>
            )}
          </div>

          {/* Example questions */}
          <div style={{ marginTop: '2rem' }}>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-disabled)', marginBottom: '0.75rem', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              Ask anything like…
            </p>
            <div className="suggested-questions">
              {EXAMPLE_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  className="suggested-q animate-fade-in-up"
                  style={{ animationDelay: `${0.5 + i * 0.05}s` }}
                  onClick={() => {
                    if (user) navigate('/chat')
                    else navigate('/login')
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features">
        <div className="container">
          <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
            <div className="badge badge-violet" style={{ marginBottom: '1rem' }}>Capabilities</div>
            <h2>Everything you need to understand a codebase</h2>
            <p style={{ maxWidth: '540px', margin: '0.75rem auto 0', fontSize: '1rem' }}>
              From a single function to the entire architecture — RepoTalk gives you a complete picture.
            </p>
          </div>

          <div className="features-grid">
            {FEATURES.map((f, i) => (
              <div key={i} className={`glass-card feature-card animate-fade-in-up`} style={{ animationDelay: `${i * 0.1}s` }}>
                <div className={`feature-icon feature-icon-${f.color}`}>{f.icon}</div>
                <div className="feature-title">{f.title}</div>
                <div className="feature-desc">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '5rem 1.5rem', textAlign: 'center', background: 'var(--bg-base)' }}>
        <div className="container container--narrow">
          <h2 style={{ marginBottom: '1rem' }}>
            Start exploring your{' '}
            <span className="gradient-text">first repository</span>
          </h2>
          <p style={{ marginBottom: '2rem', fontSize: '1rem' }}>
            No setup. No configuration. Just paste a GitHub link and start asking questions.
          </p>
          {!user && (
            <Link to="/login" className="btn btn-primary btn-lg" id="cta-signin-btn">
              <Github size={18} />
              Sign in free with GitHub
            </Link>
          )}
          {user && (
            <Link to="/chat" className="btn btn-primary btn-lg">
              Open Chat →
            </Link>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <p className="footer-text">
          RepoTalk · Built with FastAPI, React, ChromaDB, and Mistral ·{' '}
          <a href="https://github.com/Sachin-pandey13/RepoTalk" target="_blank" rel="noopener noreferrer">
            View on GitHub
          </a>
        </p>
      </footer>
    </div>
  )
}
