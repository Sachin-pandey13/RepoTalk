import { useEffect, useRef } from 'react'

const NODES = [
  { label: 'main.py',     color: '#7185FF' },
  { label: 'auth.py',     color: '#42C8E8' },
  { label: 'chat.py',     color: '#7185FF' },
  { label: 'agent.py',    color: '#42C8E8' },
  { label: 'tools.py',    color: '#37C991' },
  { label: 'embed.py',    color: '#7185FF' },
  { label: 'parser.py',   color: '#42C8E8' },
  { label: 'repo.py',     color: '#37C991' },
  { label: 'memory.py',   color: '#F2B65D' },
  { label: 'vector_db',   color: '#7185FF' },
  { label: 'config.py',   color: '#929DAD' },
  { label: 'security.py', color: '#F07178' },
  { label: 'llm.py',      color: '#42C8E8' },
  { label: 'scanner.py',  color: '#37C991' },
]

const EDGES = [
  [0,1],[0,2],[0,3],[2,3],[3,4],[3,5],[5,6],[5,9],[6,7],
  [7,8],[1,10],[1,11],[2,12],[4,5],[6,13],[9,6],[12,9],
]

export default function GraphCanvas() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animId
    let w, h
    let nodes = []

    const resize = () => {
      w = canvas.width  = canvas.offsetWidth
      h = canvas.height = canvas.offsetHeight
      initNodes()
    }

    const initNodes = () => {
      nodes = NODES.map((n, i) => ({
        ...n,
        x: 100 + Math.random() * (w - 200),
        y: 80  + Math.random() * (h - 160),
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        r: 5 + Math.random() * 3,
        phase: Math.random() * Math.PI * 2,
      }))
    }

    const draw = (t) => {
      ctx.clearRect(0, 0, w, h)

      // edges
      EDGES.forEach(([a, b]) => {
        if (!nodes[a] || !nodes[b]) return
        const na = nodes[a], nb = nodes[b]
        const dist = Math.hypot(nb.x - na.x, nb.y - na.y)
        const alpha = Math.max(0, 1 - dist / 420)
        ctx.save()
        ctx.strokeStyle = `rgba(113, 133, 255, ${alpha * 0.35})`
        ctx.lineWidth = 1
        ctx.setLineDash([4, 8])
        ctx.lineDashOffset = -(t / 30)
        ctx.beginPath()
        ctx.moveTo(na.x, na.y)
        ctx.lineTo(nb.x, nb.y)
        ctx.stroke()
        ctx.restore()
      })

      // nodes
      nodes.forEach((n, i) => {
        const pulse = Math.sin(t / 1000 + n.phase) * 0.5 + 0.5
        const glow = n.r + pulse * 4

        // glow
        const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glow * 3)
        grad.addColorStop(0, n.color + '55')
        grad.addColorStop(1, n.color + '00')
        ctx.beginPath()
        ctx.arc(n.x, n.y, glow * 3, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()

        // core dot
        ctx.beginPath()
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2)
        ctx.fillStyle = n.color
        ctx.fill()

        // label
        ctx.font = '10px "JetBrains Mono", monospace'
        ctx.fillStyle = 'rgba(233, 237, 245, 0.55)'
        ctx.textAlign = 'center'
        ctx.fillText(n.label, n.x, n.y + n.r + 14)
      })
    }

    const update = () => {
      nodes.forEach(n => {
        n.x += n.vx
        n.y += n.vy
        if (n.x < 60 || n.x > w - 60) n.vx *= -1
        if (n.y < 40 || n.y > h - 40) n.vy *= -1
      })
    }

    const loop = (t) => {
      update()
      draw(t)
      animId = requestAnimationFrame(loop)
    }

    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    resize()
    animId = requestAnimationFrame(loop)

    return () => {
      cancelAnimationFrame(animId)
      ro.disconnect()
    }
  }, [])

  return (
    <div className="graph-canvas-wrap">
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
    </div>
  )
}
