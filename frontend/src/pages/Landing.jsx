import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { GitBranch, Search, Zap, Network, ArrowRight, Star } from 'lucide-react'
import GraphCanvas from '../components/GraphCanvas'

const FEATURES = [
  {
    icon: <Search size={16} />,
    color: '#7185FF',
    title: 'Semantic Search',
    desc: 'Ask questions in plain English. Find functions, patterns, and logic instantly across the entire codebase.',
  },
  {
    icon: <Network size={16} />,
    color: '#42C8E8',
    title: 'Knowledge Graph',
    desc: 'Visualise how files, functions, and modules connect. Trace dependencies across every layer.',
  },
  {
    icon: <Zap size={16} />,
    color: '#37C991',
    title: 'AI Explanations',
    desc: 'Get precise, file-cited answers. Understand why code exists, not just what it does.',
  },
  {
    icon: <GitBranch size={16} />,
    color: '#F2B65D',
    title: 'Any Repository',
    desc: 'Paste any public GitHub URL. RepoTalk clones, parses, and indexes it in seconds.',
  },
]

export default function Landing() {
  const nav = useNavigate()

  return (
    <div className="landing">
      {/* Animated background graph */}
      <GraphCanvas />

      {/* Nav */}
      <nav className="landing-nav">
        <div className="landing-logo">
          <div className="landing-logo-mark">RT</div>
          <span className="landing-logo-name">RepoTalk</span>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <a
            href="https://github.com/Sachin-pandey13/RepoTalk"
            target="_blank"
            rel="noreferrer"
            className="btn btn-ghost btn-sm flex items-center gap-1"
          >
            <Star size={13} /> Star on GitHub
          </a>
          <button className="btn btn-secondary btn-sm" onClick={() => nav('/login')}>
            Sign in
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => nav('/login')}>
            Get started <ArrowRight size={13} />
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="landing-hero">
        <div className="hero-content">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="hero-tag">
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#37C991', display: 'inline-block', boxShadow: '0 0 6px #37C991' }} />
              AI-powered repository intelligence
            </div>
          </motion.div>

          <motion.h1
            className="hero-headline"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.08 }}
          >
            Understand your<br />
            <span className="accent">codebase.</span>
          </motion.h1>

          <motion.p
            className="hero-sub"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.16 }}
          >
            RepoTalk turns any GitHub repository into an interactive knowledge base.
            Ask questions, trace dependencies, and get AI explanations — instantly.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.24 }}
          >
            <div className="hero-input-row">
              <input
                type="text"
                placeholder="github.com/owner/repo — paste any repository URL"
                onKeyDown={e => e.key === 'Enter' && nav('/login')}
              />
              <button className="btn btn-primary" onClick={() => nav('/login')}>
                Analyse <ArrowRight size={14} />
              </button>
            </div>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 12 }}>
              Sign in with GitHub or Google to get started — it's free.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Feature strip */}
      <motion.div
        className="landing-features"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        {FEATURES.map((f, i) => (
          <div className="feature-cell" key={i}>
            <div
              className="feature-icon"
              style={{ background: f.color + '18', color: f.color, border: `1px solid ${f.color}33` }}
            >
              {f.icon}
            </div>
            <div className="feature-title">{f.title}</div>
            <div className="feature-desc">{f.desc}</div>
          </div>
        ))}
      </motion.div>
    </div>
  )
}
