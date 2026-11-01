import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Plus, Send, Trash2, RotateCcw, User, LogOut,
  BookOpen, Search, GitBranch, Cpu, ChevronRight,
  Sparkles, FileCode, Link2, AlertTriangle, CheckCircle2,
  Loader2, MessageSquare, Hash
} from 'lucide-react'

const API = 'http://localhost:8000'

const SUGGESTIONS = [
  'How does the authentication flow work?',
  'Explain the RAG pipeline step by step',
  'What does the RepositoryAgent do?',
  'How are embeddings stored and retrieved?',
  'What files handle database operations?',
  'How does streaming work in the chat route?',
]

const STATUS_CONFIG = {
  ready:    { cls: 'status-ready',    label: 'Ready',    icon: <CheckCircle2 size={10}/> },
  indexing: { cls: 'status-indexing', label: 'Indexing', icon: <Loader2 size={10} className="pulse"/> },
  cloning:  { cls: 'status-indexing', label: 'Cloning',  icon: <Loader2 size={10} className="pulse"/> },
  parsing:  { cls: 'status-indexing', label: 'Parsing',  icon: <Loader2 size={10} className="pulse"/> },
  pending:  { cls: 'status-dot pending', label: 'Pending', icon: null },
  error:    { cls: 'status-error',    label: 'Error',    icon: <AlertTriangle size={10}/> },
}

export default function Chat() {
  const nav = useNavigate()
  const [user, setUser]           = useState(null)
  const [repos, setRepos]         = useState([])
  const [activeRepo, setActiveRepo] = useState('')
  const [repoInput, setRepoInput] = useState('')
  const [ingesting, setIngesting] = useState(false)
  const [ingestMsg, setIngestMsg] = useState(null)
  const [messages, setMessages]   = useState([])
  const [question, setQuestion]   = useState('')
  const [streaming, setStreaming] = useState(false)
  const [repoStatuses, setRepoStatuses] = useState({})
  const messagesEndRef = useRef(null)
  const textareaRef    = useRef(null)
  const sourceRef      = useRef(null)
  const pollRef        = useRef({})

  // ── Auth check ──────────────────────────────────────────────
  useEffect(() => {
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(u => { if (u) setUser(u); else nav('/login') })
      .catch(() => nav('/login'))
  }, [])

  // ── Load repos ───────────────────────────────────────────────
  const loadRepos = useCallback(async () => {
    try {
      const r = await fetch(`${API}/chat/repos`, { credentials: 'include' })
      if (!r.ok) return
      const { repos: list } = await r.json()
      setRepos(list || [])
      if (list?.length && !activeRepo) setActiveRepo(list[0])
    } catch {}
  }, [activeRepo])

  useEffect(() => { if (user) loadRepos() }, [user])

  // ── Load history when repo changes ──────────────────────────
  useEffect(() => {
    if (!activeRepo) return
    setMessages([])
    fetch(`${API}/chat/history?repo_name=${encodeURIComponent(activeRepo)}`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data?.history?.length) return
        const msgs = []
        for (let i = 0; i < data.history.length; i += 2) {
          if (data.history[i])   msgs.push({ role: 'user',      content: data.history[i].content })
          if (data.history[i+1]) msgs.push({ role: 'assistant', content: data.history[i+1].content })
        }
        setMessages(msgs)
      })
      .catch(() => {})
  }, [activeRepo])

  // ── Auto-scroll ──────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Poll ingest status ───────────────────────────────────────
  const pollStatus = useCallback((repoName) => {
    if (pollRef.current[repoName]) return
    pollRef.current[repoName] = true
    const interval = setInterval(async () => {
      try {
        const r = await fetch(`${API}/chat/ingest/status/${encodeURIComponent(repoName)}`, { credentials: 'include' })
        if (!r.ok) return
        const data = await r.json()
        setRepoStatuses(p => ({ ...p, [repoName]: data.status }))
        if (data.status === 'ready' || data.status === 'error') {
          clearInterval(interval)
          delete pollRef.current[repoName]
          if (data.status === 'ready') {
            setIngestMsg({ type: 'success', text: `${repoName} is ready!` })
            setTimeout(() => setIngestMsg(null), 4000)
          }
        }
      } catch {
        clearInterval(interval)
        delete pollRef.current[repoName]
      }
    }, 3000)
  }, [])

  // ── Ingest ───────────────────────────────────────────────────
  const handleIngest = async (e) => {
    e?.preventDefault()
    const url = repoInput.trim()
    if (!url) return
    setIngesting(true)
    try {
      const r = await fetch(`${API}/chat/ingest`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: url }),
      })
      if (!r.ok) throw new Error('Ingest failed')
      const data = await r.json()
      const name = data.repo_name
      setRepoInput('')
      setRepos(p => p.includes(name) ? p : [name, ...p])
      setActiveRepo(name)
      setRepoStatuses(p => ({ ...p, [name]: 'cloning' }))
      setIngestMsg({ type: 'info', text: `Indexing ${name}…` })
      pollStatus(name)
    } catch (err) {
      setIngestMsg({ type: 'error', text: err.message })
      setTimeout(() => setIngestMsg(null), 4000)
    } finally {
      setIngesting(false)
    }
  }

  // ── Streaming ask ────────────────────────────────────────────
  const handleAsk = useCallback(async () => {
    const q = question.trim()
    if (!q || !activeRepo || streaming) return
    setQuestion('')
    setMessages(p => [...p, { role: 'user', content: q }])
    setStreaming(true)

    const assistantIdx = messages.length + 1
    setMessages(p => [...p, { role: 'assistant', content: '', streaming: true }])

    if (sourceRef.current) { sourceRef.current.close(); sourceRef.current = null }

    const url = `${API}/chat/stream?question=${encodeURIComponent(q)}&repo_name=${encodeURIComponent(activeRepo)}`
    const es = new EventSource(url, { withCredentials: true })
    sourceRef.current = es
    let buf = ''

    es.onmessage = (e) => {
      if (e.data === '[DONE]') {
        setStreaming(false)
        setMessages(p => p.map((m, i) => i === p.length - 1 ? { ...m, streaming: false } : m))
        es.close()
        sourceRef.current = null
        return
      }
      try {
        const { token, error } = JSON.parse(e.data)
        if (error) {
          setMessages(p => p.map((m, i) => i === p.length - 1
            ? { ...m, content: '⚠️ ' + error, streaming: false } : m))
          setStreaming(false)
          es.close()
          return
        }
        if (token) {
          buf += token
          setMessages(p => p.map((m, i) => i === p.length - 1 ? { ...m, content: buf } : m))
        }
      } catch {}
    }
    es.onerror = () => {
      setStreaming(false)
      setMessages(p => p.map((m, i) => i === p.length - 1 ? { ...m, streaming: false } : m))
      es.close()
      sourceRef.current = null
    }
  }, [question, activeRepo, streaming, messages.length])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleAsk()
    }
  }

  const clearHistory = async () => {
    if (!activeRepo) return
    await fetch(`${API}/chat/history?repo_name=${encodeURIComponent(activeRepo)}`, {
      method: 'DELETE', credentials: 'include'
    }).catch(() => {})
    setMessages([])
  }

  const logout = async () => {
    await fetch(`${API}/auth/logout`, { method: 'POST', credentials: 'include' })
    nav('/login')
  }

  const repoStatus = (name) => repoStatuses[name] || 'ready'

  // ── Render ───────────────────────────────────────────────────
  return (
    <div className="chat-shell">
      {/* ── Repo Sidebar ── */}
      <div className="repo-sidebar">
        <div className="repo-sidebar-header">
          <div className="logo-row">
            <div className="logo-mark">RT</div>
            <span className="logo-name">RepoTalk</span>
            <div style={{ marginLeft: 'auto' }}>
              <button className="btn btn-ghost btn-icon" onClick={logout} title="Sign out">
                <LogOut size={13} style={{ color: 'var(--steel)' }} />
              </button>
            </div>
          </div>

          {/* Add repo */}
          <form className="repo-add-form" onSubmit={handleIngest}>
            <input
              className="repo-add-input"
              value={repoInput}
              onChange={e => setRepoInput(e.target.value)}
              placeholder="github.com/owner/repo"
              disabled={ingesting}
            />
            <button className="repo-add-btn" type="submit" disabled={ingesting || !repoInput.trim()}>
              {ingesting
                ? <><Loader2 size={11} className="pulse" /> Indexing…</>
                : <><Plus size={11} /> Add Repository</>}
            </button>
          </form>
        </div>

        {/* Repo list */}
        <div className="repo-list">
          {repos.length === 0 && (
            <div style={{ padding: '20px 10px', textAlign: 'center' }}>
              <GitBranch size={20} style={{ color: 'var(--border-bright)', margin: '0 auto 8px' }} />
              <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6 }}>
                Paste a GitHub URL above to get started
              </p>
            </div>
          )}
          {repos.map(r => {
            const st = repoStatus(r)
            const cfg = STATUS_CONFIG[st] || STATUS_CONFIG.ready
            return (
              <div
                key={r}
                className={`repo-item ${activeRepo === r ? 'active' : ''}`}
                onClick={() => setActiveRepo(r)}
              >
                <div className={`status-dot ${cfg.cls}`} />
                <span className="repo-name">{r}</span>
                <span className={`repo-status-tag status-${st}`}>{cfg.label}</span>
              </div>
            )
          })}
        </div>

        {/* Bottom nav */}
        <div className="sidebar-nav">
          {user && (
            <div className="sidebar-nav-item" onClick={() => nav('/profile')}>
              {user.avatar_url
                ? <img src={user.avatar_url} style={{ width: 20, height: 20, borderRadius: '50%' }} />
                : <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'var(--indigo)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, color: 'white' }}>
                    {(user.name || user.username || 'U')[0].toUpperCase()}
                  </div>
              }
              <span style={{ fontSize: 12, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.name || user.username}
              </span>
              <ChevronRight size={11} style={{ color: 'var(--muted)' }} />
            </div>
          )}
        </div>
      </div>

      {/* ── Chat Main ── */}
      <div className="chat-main">
        {/* Topbar */}
        <div className="chat-topbar">
          <Cpu size={14} style={{ color: 'var(--indigo)' }} />
          <span className="chat-topbar-title">Repository Intelligence</span>
          {activeRepo && (
            <>
              <ChevronRight size={12} style={{ color: 'var(--muted)' }} />
              <span className="chat-topbar-repo">{activeRepo}</span>
            </>
          )}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
            {activeRepo && messages.length > 0 && (
              <button className="btn btn-ghost btn-sm flex items-center gap-1" onClick={clearHistory}>
                <Trash2 size={12} /> Clear
              </button>
            )}
          </div>
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {!activeRepo ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">
                <GitBranch size={22} style={{ color: 'var(--indigo)' }} />
              </div>
              <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--cloud)', marginBottom: 8 }}>
                No repository selected
              </h2>
              <p style={{ fontSize: 13, color: 'var(--steel)', lineHeight: 1.7, maxWidth: 320 }}>
                Add a GitHub repository URL in the sidebar to start asking questions about any codebase.
              </p>
            </div>
          ) : messages.length === 0 ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">
                <Sparkles size={22} style={{ color: 'var(--indigo)' }} />
              </div>
              <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--cloud)', marginBottom: 6 }}>
                Ask anything about <span style={{ color: 'var(--indigo)' }}>{activeRepo}</span>
              </h2>
              <p style={{ fontSize: 13, color: 'var(--steel)', lineHeight: 1.7, maxWidth: 380 }}>
                Questions are answered with exact file citations and code-level evidence from the repository.
              </p>
              <div className="suggestions-grid">
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} className="suggestion-chip" onClick={() => setQuestion(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((m, i) => (
                <motion.div
                  key={i}
                  className={`message ${m.role}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  <div className="message-bubble">
                    {m.role === 'assistant' ? (
                      <div className="md-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.content || ' '}
                        </ReactMarkdown>
                        {m.streaming && <span className="streaming-cursor" />}
                      </div>
                    ) : (
                      m.content
                    )}
                  </div>
                  <div className="message-meta">
                    {m.role === 'assistant' ? (
                      <span className="ai-tag">
                        <Sparkles size={10} /> RepoTalk AI
                      </span>
                    ) : (
                      <span><User size={10} /> You</span>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
          <div ref={messagesEndRef} style={{ height: 1 }} />
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <div className="chat-input-box">
            <textarea
              ref={textareaRef}
              rows={1}
              value={question}
              onChange={e => {
                setQuestion(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
              }}
              onKeyDown={handleKeyDown}
              placeholder={activeRepo ? `Ask anything about ${activeRepo}…` : 'Select a repository to start chatting'}
              disabled={!activeRepo || streaming}
            />
            <button
              className="chat-send-btn"
              onClick={handleAsk}
              disabled={!question.trim() || !activeRepo || streaming}
            >
              {streaming
                ? <Loader2 size={14} className="pulse" />
                : <Send size={14} />}
            </button>
          </div>
          <div className="chat-input-hint">
            <span className="kbd">Enter</span> to send
            <span style={{ color: 'var(--border-bright)' }}>·</span>
            <span className="kbd">Shift+Enter</span> new line
            {streaming && (
              <>
                <span style={{ color: 'var(--border-bright)' }}>·</span>
                <span style={{ color: 'var(--ice)', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <Sparkles size={10} /> AI is responding…
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Ingest toast */}
      <AnimatePresence>
        {ingestMsg && (
          <motion.div
            className="ingest-toast"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {ingestMsg.type === 'success' && <CheckCircle2 size={16} style={{ color: 'var(--mint)', flexShrink: 0 }} />}
              {ingestMsg.type === 'error'   && <AlertTriangle size={16} style={{ color: 'var(--coral)', flexShrink: 0 }} />}
              {ingestMsg.type === 'info'    && (
                <div style={{ width: 16, flexShrink: 0 }}>
                  <div className="spinner" style={{ width: 14, height: 14 }} />
                </div>
              )}
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--cloud)', marginBottom: 4 }}>
                  {ingestMsg.type === 'success' ? 'Repository ready!' : ingestMsg.type === 'error' ? 'Ingest failed' : 'Indexing repository'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--steel)' }}>{ingestMsg.text}</div>
                {ingestMsg.type === 'info' && (
                  <div className="progress-bar-wrap" style={{ marginTop: 8 }}>
                    <div className="progress-bar-fill indeterminate" />
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
