import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceArea,
  ZAxis,
} from 'recharts'
import { memo, useMemo } from 'react'

const QUADRANT_COLORS = {
  star: 'var(--success)',
  plowhorse: 'var(--info)',
  puzzle: 'var(--warning)',
  dog: 'var(--danger)',
}

const QUADRANT_LABELS = {
  star: { label: 'STAR', x: 75, y: 78 },
  puzzle: { label: 'PUZZLE', x: 25, y: 78 },
  plowhorse: { label: 'PLOWHORSE', x: 75, y: 24 },
  dog: { label: 'UNDERPERFORMER', x: 25, y: 24 },
}

const QUADRANT_LEGEND = [
  { key: 'star', label: 'Star', color: 'var(--success)' },
  { key: 'puzzle', label: 'Puzzle', color: 'var(--warning)' },
  { key: 'plowhorse', label: 'Plowhorse', color: 'var(--info)' },
  { key: 'dog', label: 'Underperformer', color: 'var(--danger)' },
]

function CustomTooltip({ payload }) {
  if (!payload || !payload[0]) return null
  const item = payload[0].payload
  const qColor = QUADRANT_COLORS[item.quadrant] || 'var(--text-muted)'

  return (
    <div
      style={{
        background: 'var(--bg-overlay)',
        border: '1px solid var(--border-strong)',
        borderRadius: 'var(--radius-md)',
        padding: 'var(--space-4)',
        fontSize: 12,
        fontFamily: 'var(--font-body)',
        minWidth: 220,
        boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
        color: '#FFFFFF'
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 14, color: '#FFFFFF', marginBottom: 6 }}>{item.name}</div>
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '2px 8px',
          borderRadius: 'var(--radius-full)',
          background: `color-mix(in srgb, ${qColor} 15%, transparent)`,
          color: qColor,
          fontSize: 10,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          marginBottom: 8,
        }}
      >
        {item.quadrant?.replace('_', ' ')}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.7)' }}>
          <span>Popularity</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>{item.x.toFixed(0)} / 100</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.7)' }}>
          <span>CM%</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>{item.y.toFixed(1)}%</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'rgba(255,255,255,0.7)' }}>
          <span>Price</span>
          <span style={{ fontFamily: 'var(--font-mono)', color: '#FFFFFF' }}>₹{item.selling_price}</span>
        </div>
      </div>
      {item.action_recommendation && (
        <div style={{ marginTop: 8, paddingTop: 6, borderTop: '1px solid var(--border-subtle)', fontSize: 11, color: 'var(--text-secondary)' }}>
          {item.action_recommendation}
        </div>
      )}
    </div>
  )
}

function MenuMatrix({ items }) {
  if (!items || items.length === 0) return null

  const chartData = useMemo(() => {
    const withValues = items
      .map((item) => {
        const popularityRaw = Number(item.popularity_score || 0)
        const popularity = popularityRaw <= 1 ? popularityRaw * 100 : popularityRaw
        const margin = Number(item.margin_pct || item.cm_percent || 0)
        const sizeSource = Number(item.daily_velocity || item.units_sold || item.total_revenue || 1)

        return {
          x: Number.isFinite(popularity) ? popularity : 0,
          y: Number.isFinite(margin) ? margin : 0,
          z: Math.max(1, sizeSource),
          name: item.name,
          quadrant: item.quadrant,
          action_recommendation: item.action || item.action_recommendation || 'Maintain visibility',
          selling_price: item.selling_price,
        }
      })
      .filter((item) => Number.isFinite(item.x) && Number.isFinite(item.y))

    return withValues
  }, [items])

  return (
    <div style={{ position: 'relative' }}>
      <ResponsiveContainer width="100%" height={430}>
        <ScatterChart margin={{ top: 20, right: 24, bottom: 42, left: 52 }}>
          <ReferenceArea x1={50} x2={100} y1={50} y2={100} fill="rgba(42,122,80,0.06)" />
          <ReferenceArea x1={0} x2={50} y1={50} y2={100} fill="rgba(192,122,32,0.08)" />
          <ReferenceArea x1={50} x2={100} y1={0} y2={50} fill="rgba(42,90,140,0.07)" />
          <ReferenceArea x1={0} x2={50} y1={0} y2={50} fill="rgba(140,42,42,0.08)" />

          <XAxis
            dataKey="x"
            type="number"
            name="Popularity"
            domain={[0, 100]}
            tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
            label={{ value: 'Popularity Score (0-100)', position: 'bottom', fill: 'var(--text-secondary)', fontSize: 11, offset: 12 }}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="Contribution Margin"
            domain={[0, 100]}
            tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            tickLine={false}
            label={{ value: 'Contribution Margin %', angle: -90, position: 'left', fill: 'var(--text-secondary)', fontSize: 11, offset: 10 }}
          />
          <ZAxis dataKey="z" range={[70, 260]} />
          <Tooltip content={<CustomTooltip />} />
          <Scatter data={chartData} isAnimationActive animationDuration={450}>
            {chartData.map((entry, index) => (
              <Cell key={index} fill={QUADRANT_COLORS[entry.quadrant] || 'var(--text-muted)'} fillOpacity={0.88} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {Object.entries(QUADRANT_LABELS).map(([key, pos]) => (
        <div
          key={key}
          style={{
            position: 'absolute',
            top: `${100 - pos.y}%`,
            left: `${pos.x}%`,
            transform: 'translate(-50%, -50%)',
            fontFamily: 'var(--font-body)',
            fontSize: 11,
            fontWeight: 800,
            color: 'var(--text-primary)',
            opacity: 0.22,
            pointerEvents: 'none',
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
          }}
        >
          {pos.label}
        </div>
      ))}

      <div className="menu-matrix-legend">
        {QUADRANT_LEGEND.map((item) => (
          <div key={item.key} className="menu-matrix-legend-item">
            <span className="menu-matrix-legend-dot" style={{ background: item.color }} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default memo(MenuMatrix)
