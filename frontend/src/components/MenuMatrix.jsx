import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const QUADRANT_COLORS = {
  star: 'var(--green)',
  'hidden_star': 'var(--purple)',
  workhorse: 'var(--amber)',
  dog: 'var(--gray)',
}

export default function MenuMatrix({ items }) {
  if (!items || items.length === 0) return null

  const chartData = items.map(item => ({
    x: item.popularity_score,
    y: item.cm_percent,
    z: item.units_sold || 10, // dot size
    name: item.name,
    quadrant: item.quadrant,
    action_recommendation: item.action_recommendation || 'Maintain',
  }))

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ position: 'absolute', top: 8, left: 60, fontSize: 11, color: 'var(--text-muted)', zIndex: 1 }}>
        <span style={{ color: 'var(--purple)' }}>🔮 Hidden Stars</span> (High Margin, Low Pop)
      </div>
      <div style={{ position: 'absolute', top: 8, right: 16, fontSize: 11, color: 'var(--text-muted)', zIndex: 1 }}>
        <span style={{ color: 'var(--green)' }}>⭐ Stars</span> (High Margin, High Pop)
      </div>
      <div style={{ position: 'absolute', bottom: 30, left: 60, fontSize: 11, color: 'var(--text-muted)', zIndex: 1 }}>
        <span style={{ color: 'var(--gray)' }}>🐕 Dogs</span> (Low Margin, Low Pop)
      </div>
      <div style={{ position: 'absolute', bottom: 30, right: 16, fontSize: 11, color: 'var(--text-muted)', zIndex: 1 }}>
        <span style={{ color: 'var(--amber)' }}>🐴 Workhorses</span> (Low Margin, High Pop)
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 30, right: 20, bottom: 20, left: 20 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis
            dataKey="x"
            type="number"
            name="Popularity"
            domain={[0, 100]} // popularity goes 0-100 as per Person A desc
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            label={{ value: 'Popularity →', position: 'bottom', fill: 'var(--text-muted)', fontSize: 11 }}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="CM %"
            domain={[0, 100]}
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
            label={{ value: 'CM % →', angle: -90, position: 'insideLeft', fill: 'var(--text-muted)', fontSize: 11 }}
          />
          <Tooltip
            content={({ payload }) => {
              if (!payload || !payload[0]) return null
              const item = payload[0].payload
              return (
                <div style={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
                  <div style={{ fontWeight: 600 }}>{item.name}</div>
                  <div style={{ color: 'var(--text-muted)' }}>Popularity: {item.x?.toFixed(1)}</div>
                  <div style={{ color: 'var(--text-muted)' }}>CM%: {item.y?.toFixed(1)}%</div>
                  <div style={{ color: 'var(--text-muted)' }}>Action: <strong style={{ color: QUADRANT_COLORS[item.quadrant] || 'var(--text)' }}>{item.action_recommendation}</strong></div>
                  <div style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>Quadrant: {item.quadrant?.replace('_', ' ')}</div>
                </div>
              )
            }}
          />
          <Scatter data={chartData} dataKey="z" shape="circle">
            {chartData.map((entry, idx) => (
              <Cell key={idx} fill={QUADRANT_COLORS[entry.quadrant] || '#888'} opacity={0.8} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
