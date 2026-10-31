import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Send, Plus, ChevronRight, ChevronLeft, RefreshCw,
  GitBranch, Loader2, AlertCircle, CheckCircle2, X, Trash2
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const SUGGESTED = [
  'Explain the overall architecture',
  'How does authentication work?',
  'What are the main data models?',
  'Walk me through the request lifecycle',
  'How do I run this project locally?',
  'What are the entry points?',
]

function RepoPanel({ repos, activeRepo, onSelectRepo, onIngest, collapsed, onToggle }) {
  const [url, setUrl] = useState('')
  const [ingesting, setIngesting] = useState(false)
  const [status, setStatus] = useState(null) // {type:'success'|'error', text}

  const handleIngest = async () => {
    if (!url.trim()) return
    setIngesting(true)
    setStatus(null)
    try {
      const resp = await fetch(`${API}/chat/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ repo_url: url }),
      })
      const data = await resp.json()
      if (resp.ok) {
        setStatus({ type: 'success', text: `"${data.repo_name}" ingested ✓` })
        setUrl('')
        onIngest(data.repo_name)
      } else {
        setStatus({ type: 'error', text: data.detail || 'Ingestion failed' })
      }
    } catch (e) {
      setStatus({ type: 'error', text: 'Network error' })
    }
    setIngesting(false)
  }

  if (collapsed) {
    return (
      <aside className="sidebar sidebar--collapsed">
        <button className="sidebar-toggle" onClick={onToggle} title="Expand sidebar">
          <ChevronRight size={16} />
        </button>
      </aside>
    )
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">
          <GitBranch size={15} />
          Repositories
        </div>
        <button className="sidebar-toggle" onClick={onToggle} title="Collapse sidebar">
          <ChevronLeft size={16} />
        </button>
      </div>

      {/* Ingest input */}
      <div className="sidebar-ingest">
        <input
          id="repo-url-input"
          className="sidebar-url-input"
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleIngest()}
          placeholder="https://github.com/owner/repo"
          disabled={ingesting}
        />
        <button
          id="ingest-btn"
          className="btn btn-primary btn-sm"
          style={{ width: '100%', marginTop: '0.5rem', justifyContent: 'center' }}
          onClick={handleIngest}
          disabled={ingesting || !url.trim()}
        >
          {ingesting ? <Loader2 size={14} className="spin" /> : <Plus size={14} />}
          {ingesting ? 'Indexing…' : 'Add Repo'}
        </button>

        {status && (
          <div className={`ingest-status ingest-status--${status.type}`}>
            {status.type === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
            {status.text}
          </div>
        )}
      </div>

      {/* Repo list */}
      <div className="sidebar-repos">
        {repos.length === 0 && (
          <div className="sidebar-empty">No repositories yet</div>
        )}
        {repos.map((r, i) => (
          <button
            key={i}
            className={`sidebar-repo${activeRepo === r ? ' active' : ''}`}
            onClick={() => onSelectRepo(r)}
          >
            <GitBranch size={13} />
            <span className="sidebar-repo-name">{r}</span>
          </button>
        ))}
      </div>
    </aside>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`message message--${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🧠'}
      </div>
      <div className="message-bubble">
        {isUser ? (
          <p>{msg.content}</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
        )}
        {msg.streaming && <span className="cursor-blink" />}
      </div>
    </div>
  )
}

export default function Chat() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [repos, setRepos] = useState([])
  const [activeRepo, setActiveRepo] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [error, setError] = useState(null)

  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const esRef = useRef(null)

  // Redirect if not logged in
  useEffect(() => {
    if (!loading && !user) navigate('/login', { replace: true })
  }, [user, loading, navigate])

  // Load repos
  const loadRepos = useCallback(async () => {
    try {
      const resp = await fetch(`${API}/chat/repos`, { credentials: 'include' })
      if (resp.ok) {
        const data = await resp.json()
        setRepos(data.repos || [])
      }
    } catch {}
  }, [])

  useEffect(() => { loadRepos() }, [loadRepos])

  // Handle ?repo= param from landing page ingest
  useEffect(() => {
    const repoParam = searchParams.get('repo')
    if (repoParam) {
      setActiveRepo(repoParam)
      setSearchParams({}, { replace: true })
    }
  }, [searchParams, setSearchParams])

  // Load history when activeRepo changes
  useEffect(() => {
    if (!activeRepo) return
    setMessages([])
    const load = async () => {
      try {
        const resp = await fetch(
          `${API}/chat/history?repo_name=${encodeURIComponent(activeRepo)}`,
          { credentials: 'include' }
        )
        if (resp.ok) {
          const data = await resp.json()
          setMessages(data.history || [])
        }
      } catch {}
    }
    load()
  }, [activeRepo])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    const question = text || input.trim()
    if (!question || streaming || !activeRepo) return

    setInput('')
    setError(null)

    // Append user message
    setMessages(prev => [...prev, { role: 'user', content: question }])

    // Append placeholder for assistant
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])
    setStreaming(true)

    try {
      // Close previous stream if open
      if (esRef.current) esRef.current.close()

      const streamUrl = new URL(`${API}/chat/stream`)
      streamUrl.searchParams.set('question', question)
      streamUrl.searchParams.set('repo_name', activeRepo)

      const es = new EventSource(streamUrl.toString(), { withCredentials: true })
      esRef.current = es

      es.onmessage = (e) => {
        if (e.data === '[DONE]') {
          es.close()
          setStreaming(false)
          setMessages(prev => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last?.streaming) last.streaming = false
            return copy
          })
          return
        }
        try {
          const chunk = JSON.parse(e.data)
          if (chunk.token) {
            setMessages(prev => {
              const copy = [...prev]
              const last = copy[copy.length - 1]
              if (last?.role === 'assistant') {
                last.content += chunk.token
              }
              return copy
            })
          }
          if (chunk.error) {
            setError(chunk.error)
            es.close()
            setStreaming(false)
          }
        } catch {}
      }

      es.onerror = () => {
        es.close()
        setStreaming(false)
        setMessages(prev => {
          const copy = [...prev]
          const last = copy[copy.length - 1]
          if (last?.streaming) last.streaming = false
          return copy
        })
        setError('Stream error — please try again.')
      }
    } catch (e) {
      setStreaming(false)
      setError(e.message)
    }
  }

  const clearHistory = async () => {
    if (!activeRepo) return
    setMessages([])
    try {
      await fetch(`${API}/chat/history?repo_name=${encodeURIComponent(activeRepo)}`, {
        method: 'DELETE',
        credentials: 'include',
      })
    } catch {}
  }

  const onIngest = (repoName) => {
    setRepos(prev => prev.includes(repoName) ? prev : [...prev, repoName])
    setActiveRepo(repoName)
    setMessages([])
  }

  if (loading) return null

  return (
    <div className="chat-layout">
      {/* Sidebar */}
      <RepoPanel
        repos={repos}
        activeRepo={activeRepo}
        onSelectRepo={(r) => { setActiveRepo(r); setMessages([]) }}
        onIngest={onIngest}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(p => !p)}
      />

      {/* Main chat area */}
      <main className="chat-main">
        {/* Chat header */}
        <div className="chat-header">
          <div className="chat-header-left">
            {activeRepo ? (
              <>
                <GitBranch size={16} color="var(--violet-400)" />
                <span className="chat-repo-name">{activeRepo}</span>
              </>
            ) : (
              <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                Select or add a repository to start chatting
              </span>
            )}
          </div>
          {activeRepo && messages.length > 0 && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={clearHistory}
              title="Clear conversation"
            >
              <Trash2 size={14} />
              Clear
            </button>
          )}
        </div>

        {/* Messages */}
        <div className="chat-messages">
          {!activeRepo && (
            <div className="chat-empty">
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🧠</div>
              <h3>Add a repository to start</h3>
              <p>Paste a GitHub URL in the sidebar to index it, then ask anything about the code.</p>
            </div>
          )}

          {activeRepo && messages.length === 0 && (
            <div className="chat-empty">
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>💬</div>
              <h3>Ask anything about <span className="gradient-text">{activeRepo}</span></h3>
              <div className="suggested-questions" style={{ marginTop: '1.5rem' }}>
                {SUGGESTED.map((q, i) => (
                  <button
                    key={i}
                    className="suggested-q"
                    onClick={() => sendMessage(q)}
                    disabled={streaming}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <Message key={i} msg={msg} />
          ))}

          {error && (
            <div className="chat-error">
              <AlertCircle size={14} />
              {error}
              <button onClick={() => setError(null)}><X size={12} /></button>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div className="chat-input-bar">
          <div className={`chat-input-wrap${streaming ? ' streaming' : ''}`}>
            <textarea
              id="chat-input"
              ref={inputRef}
              className="chat-textarea"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
              placeholder={activeRepo ? 'Ask about the code… (Enter to send, Shift+Enter for new line)' : 'Select a repository first'}
              disabled={!activeRepo || streaming}
              rows={1}
            />
            <button
              id="send-btn"
              className="send-btn"
              onClick={() => sendMessage()}
              disabled={!activeRepo || streaming || !input.trim()}
            >
              {streaming ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
            </button>
          </div>
          <p className="chat-hint">
            Powered by Mistral + ChromaDB · Citations include file names &amp; line numbers
          </p>
        </div>
      </main>
    </div>
  )
}
