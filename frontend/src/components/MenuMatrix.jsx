import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceArea } from 'recharts'
import { useState, useEffect } from 'react'

const QUADRANT_COLORS = {
  star: 'var(--success)',
  'hidden_star': 'var(--data-5)',
  workhorse: 'var(--warning)',
  dog: 'var(--danger)',
}

const QUADRANT_LABELS = {
  star: { label: 'STAR', x: 75, y: 75 },
  hidden_star: { label: 'PUZZLE', x: 25, y: 75 },
  workhorse: { label: 'PLOWHORSE', x: 75, y: 25 },
  dog: { label: 'DOG', x: 25, y: 25 },
}

function CustomTooltip({ payload }) {
  if (!payload || !payload[0]) return null
  const item = payload[0].payload
  const qColor = QUADRANT_COLORS[item.quadrant] || 'var(--text-muted)'

  return (
    <div style={{
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-mid)',
      borderRadius: 'var(--radius-md)',
      padding: 'var(--space-4)',
      fontSize: 12,
      fontFamily: 'var(--font-body)',
      minWidth: 200,
      boxShadow: 'var(--shadow-lg)',
    }}>
      <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)', marginBottom: 6 }}>{item.name}</div>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '2px 8px', borderRadius: 'var(--radius-full)', background: `color-mix(in srgb, ${qColor} 15%, transparent)`, color: qColor, fontSize: 10, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
        {item.quadrant?.replace('_', ' ')}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
          <span>Popularity</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{item.x?.toFixed(0)} / 100</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
          <span>CM%</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{item.y?.toFixed(1)}%</span>
        </div>
        {item.selling_price && (
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
            <span>Price</span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>₹{item.selling_price}</span>
          </div>
        )}
      </div>
      {item.action_recommendation && (
        <div style={{ marginTop: 8, paddingTop: 6, borderTop: '1px solid var(--border-subtle)', fontSize: 11, fontStyle: 'italic', color: 'var(--text-secondary)' }}>
          {item.action_recommendation}
        </div>
      )}
    </div>
  )
}

export default function MenuMatrix({ items }) {
  const [animated, setAnimated] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 100)
    return () => clearTimeout(timer)
  }, [])

  if (!items || items.length === 0) return null

  const maxRevenue = Math.max(...items.map(i => i.units_sold || i.total_revenue || 10))
  const minRevenue = Math.min(...items.map(i => i.units_sold || i.total_revenue || 1))

  const chartData = items.map(item => {
    const rev = item.units_sold || item.total_revenue || 10
    const normSize = 6 + ((rev - minRevenue) / (maxRevenue - minRevenue || 1)) * 12
    return {
      x: animated ? item.popularity_score : 50,
      y: animated ? item.cm_percent : 50,
      z: normSize,
      name: item.name,
      quadrant: item.quadrant,
      action_recommendation: item.action_recommendation || 'Maintain',
      selling_price: item.selling_price,
    }
  })

  return (
    <div style={{ position: 'relative' }}>
      <ResponsiveContainer width="100%" height={420}>
        <ScatterChart margin={{ top: 20, right: 20, bottom: 30, left: 20 }}>
          {/* Quadrant background fills */}
          <ReferenceArea x1={50} x2={100} y1={50} y2={100} fill="rgba(42,122,80,0.05)" />
          <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill="rgba(42,90,140,0.05)" />
          <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill="rgba(192,122,32,0.05)" />
          <ReferenceArea x1={0} x2={50} y1={0} y2={50} fill="rgba(140,42,42,0.05)" />

          <XAxis
            dataKey="x"
            type="number"
            name="Popularity"
            domain={[0, 100]}
            tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'JetBrains Mono' }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
            label={{ value: 'Popularity Score →', position: 'bottom', fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'Sora', offset: 12 }}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="CM %"
            domain={[0, 100]}
            tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'JetBrains Mono' }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
            label={{ value: '← Contribution Margin %', angle: -90, position: 'insideLeft', fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'Sora' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Scatter data={chartData} dataKey="z" shape="circle" isAnimationActive={true} animationDuration={800}>
            {chartData.map((entry, idx) => (
              <Cell key={idx} fill={QUADRANT_COLORS[entry.quadrant] || 'var(--text-muted)'} fillOpacity={0.85} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Quadrant watermark labels */}
      {Object.entries(QUADRANT_LABELS).map(([key, pos]) => (
        <div key={key} style={{
          position: 'absolute',
          top: `${100 - pos.y}%`,
          left: `${pos.x}%`,
          transform: 'translate(-50%, -50%)',
          fontFamily: 'var(--font-display)',
          fontSize: 28,
          fontWeight: 900,
          color: 'var(--text-primary)',
          opacity: 0.06,
          pointerEvents: 'none',
          letterSpacing: '0.05em',
        }}>
          {pos.label}
        </div>
      ))}
    </div>
  )
}
