import { motion, useInView } from 'motion/react'
import { useRef, useEffect, useState } from 'react'

function AnimatedValue({ value, isInView }) {
  const [display, setDisplay] = useState(value)
  const prevRef = useRef(value)

  useEffect(() => {
    if (!isInView) return
    // Try to extract a number for count-up
    const raw = typeof value === 'string' ? value.replace(/[^0-9.-]/g, '') : value
    const num = parseFloat(raw)
    if (isNaN(num) || (typeof value === 'string' && !/[\d]/.test(value))) {
      setDisplay(value)
      return
    }

    const start = 0
    const startTime = performance.now()
    const duration = 600

    const animate = (now) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      const current = start + (num - start) * eased

      // Reconstruct the formatted string
      if (typeof value === 'string') {
        const prefix = value.match(/^[^\d.-]*/)?.[0] || ''
        const suffix = value.match(/[^\d.,]*$/)?.[0] || ''
        const formatted = Number.isInteger(num) ? Math.round(current).toLocaleString('en-IN') : current.toFixed(1)
        setDisplay(`${prefix}${formatted}${suffix}`)
      } else {
        setDisplay(Math.round(current))
      }

      if (progress < 1) requestAnimationFrame(animate)
      else setDisplay(value)
    }
    requestAnimationFrame(animate)
    prevRef.current = value
  }, [isInView, value])

  return <>{display}</>
}

export default function MetricCard({ label, value, suffix = '', color, icon, trend }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })

  const semanticColor = color || 'var(--accent)'

  return (
    <motion.div
      ref={ref}
      className="card"
      style={{ cursor: 'default' }}
      whileHover={{ y: -2, borderColor: 'var(--border-mid)', transition: { duration: 0.15 } }}
    >
      <div className="card-body" style={{ padding: 'var(--space-6, 24px)' }}>
        {/* Icon + Label row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3, 12px)', marginBottom: 'var(--space-4, 16px)' }}>
          <div style={{
            width: 40, height: 40,
            borderRadius: 'var(--radius-md, 8px)',
            background: `color-mix(in srgb, ${semanticColor} 10%, transparent)`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 20, flexShrink: 0,
          }}>
            {icon}
          </div>
          <span style={{
            fontFamily: 'var(--font-body)',
            fontSize: 11,
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: 'var(--text-secondary)',
          }}>
            {label}
          </span>
        </div>

        {/* Big number */}
        <motion.div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 32,
            fontWeight: 600,
            color: 'var(--text-primary)',
            lineHeight: 1.1,
            fontVariantNumeric: 'tabular-nums',
          }}
          initial={{ opacity: 0, y: 10 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <AnimatedValue value={value} isInView={isInView} />
          {suffix && (
            <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 6 }}>
              {suffix}
            </span>
          )}
        </motion.div>

        {/* Trend indicator */}
        {trend && (
          <div style={{
            marginTop: 'var(--space-2, 8px)',
            fontSize: 12,
            fontFamily: 'var(--font-body)',
            color: trend.direction === 'up' ? 'var(--success)' : trend.direction === 'down' ? 'var(--danger)' : 'var(--text-muted)',
          }}>
            {trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→'} {trend.label}
          </div>
        )}
      </div>
    </motion.div>
  )
}
