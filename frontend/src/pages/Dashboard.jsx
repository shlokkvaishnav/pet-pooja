import { useState, useEffect } from 'react'
import { getDashboardMetrics, getHiddenStars, getRisks, getCategoryBreakdown, getTrends } from '../api/client'
import MetricCard from '../components/MetricCard'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [hiddenStars, setHiddenStars] = useState([])
  const [riskItems, setRiskItems] = useState([])
  const [categoryData, setCategoryData] = useState([])
  const [trends, setTrends] = useState(null)
  const [showHealthBreakdown, setShowHealthBreakdown] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getDashboardMetrics(),
      getHiddenStars(),
      getRisks(),
      getCategoryBreakdown(),
      getTrends().catch(() => null),
    ])
      .then(([metricsData, hiddenStarsData, risksData, categoryBreakdown, trendsData]) => {
        setMetrics(metricsData)
        setHiddenStars(hiddenStarsData.slice(0, 3) || [])
        setRiskItems(risksData.slice(0, 3) || [])
        setCategoryData(categoryBreakdown || [])
        setTrends(trendsData)
      })
      .catch(err => console.error('Dashboard data load failed:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="loading"><div className="spinner" /> Loading dashboard...</div>
  }

  if (!metrics) {
    return <div className="loading">Failed to load data. Is the backend running?</div>
  }

  const healthBreakdown = metrics.health_score_breakdown || {}
  const driftItems = trends?.quadrant_drift || []
  const peakHours = metrics.peak_hours || []

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Revenue intelligence overview — all metrics at a glance</p>
      </div>

      {/* KPI Cards — Row 1: Strategic */}
      <div className="grid-4" style={{ marginBottom: 16 }}>
        <MetricCard
          label="Total Revenue"
          value={`₹${metrics.total_revenue?.toLocaleString() || 0}`}
          color="var(--blue)"
          icon="💰"
        />
        <MetricCard
          label="Avg CM%"
          value={`${metrics.avg_cm_percent || 0}%`}
          color="var(--green)"
          icon="📈"
        />
        <MetricCard
          label="Items At Risk"
          value={metrics.items_at_risk_count || 0}
          color="var(--red)"
          icon="⚠️"
        />
        <MetricCard
          label="Uplift Potential"
          value={`₹${metrics.uplift_potential?.toLocaleString() || 0}`}
          color="var(--amber)"
          icon="🚀"
        />
      </div>

      {/* KPI Cards — Row 2: Operational */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <MetricCard
          label="Avg Order Value"
          value={`₹${metrics.avg_order_value?.toLocaleString() || 0}`}
          color="var(--purple)"
          icon="🧾"
        />
        <MetricCard
          label="Total Orders (30d)"
          value={metrics.total_orders || 0}
          color="var(--blue)"
          icon="📋"
        />
        <div
          className="card"
          style={{ cursor: 'pointer', position: 'relative' }}
          onClick={() => setShowHealthBreakdown(!showHealthBreakdown)}
        >
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 16 }}>
            <div>
              <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: 1 }}>
                Health Score <span style={{ fontSize: 10, opacity: 0.7 }}>ⓘ click</span>
              </div>
              <div style={{ fontSize: 26, fontWeight: 700, color: metrics.health_score >= 60 ? 'var(--green)' : metrics.health_score >= 40 ? 'var(--amber)' : 'var(--red)' }}>
                {metrics.health_score || 0}
              </div>
            </div>
            <div style={{ fontSize: 28 }}>🏥</div>
          </div>
        </div>
        <MetricCard
          label="Peak Hour"
          value={peakHours[0]?.label || '—'}
          suffix={peakHours[0] ? `(${peakHours[0].order_count} orders)` : ''}
          color="var(--amber)"
          icon="⏰"
        />
      </div>

      {/* Health Score Breakdown (collapsible) */}
      {showHealthBreakdown && healthBreakdown.components && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">🏥 Health Score Breakdown</div>
          <div className="card-body">
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
              {healthBreakdown.explanation}
            </p>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              {healthBreakdown.components.map((c, i) => (
                <div key={i} style={{
                  flex: '1 1 200px',
                  padding: 12,
                  background: 'var(--surface2)',
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>{c.name}</div>
                  <div style={{
                    fontSize: 20, fontWeight: 700,
                    color: c.score >= 0 ? 'var(--green)' : 'var(--red)',
                  }}>
                    {c.score > 0 ? '+' : ''}{c.score} <span style={{ fontSize: 11, fontWeight: 400 }}>/ {c.max}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{c.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* CM% Per Category Chart */}
        <div className="card">
          <div className="card-header">📊 Average CM% per Category</div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryData} margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                <XAxis dataKey="category" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <Tooltip cursor={{ fill: 'var(--surface2)' }} contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }} />
                <Bar dataKey="avg_cm_pct" fill="var(--blue)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Peak Hours Chart */}
        <div className="card">
          <div className="card-header">⏰ Orders by Hour</div>
          <div className="card-body">
            {peakHours.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No hourly data available.</div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={peakHours.sort((a, b) => a.hour - b.hour)} margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                  <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                  <Tooltip contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }} />
                  <Bar dataKey="order_count" fill="var(--purple)" radius={[4, 4, 0, 0]} name="Orders" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Quick View Lists */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header" style={{ color: 'var(--purple)' }}>🔍 Top 3 Hidden Stars</div>
            <div className="card-body">
              {hiddenStars.length === 0 ? <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No hidden stars found.</div> : hiddenStars.map(item => (
                <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 13 }}>{item.name}</span>
                  <span style={{ fontSize: 12, color: 'var(--purple)', fontWeight: 600 }}>CM: {item.cm_percent || item.margin_pct}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-header" style={{ color: 'var(--red)' }}>⚠️ Top 3 Risk Items</div>
            <div className="card-body">
              {riskItems.length === 0 ? <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No items at risk.</div> : riskItems.map(item => (
                <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 13 }}>{item.name}</span>
                  <span style={{ fontSize: 12, color: 'var(--red)', fontWeight: 600 }}>CM: {item.cm_percent || item.margin_pct}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quadrant Drift Alerts */}
        <div className="card">
          <div className="card-header" style={{ color: 'var(--amber)' }}>📈 Quadrant Drift Alerts</div>
          <div className="card-body">
            {driftItems.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No significant quadrant shifts detected.</div>
            ) : driftItems.slice(0, 5).map((item, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{item.name}</span>
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 4,
                    background: item.drift_direction.includes('dog') || item.drift_direction.includes('→ dog') ? 'var(--red)' : 'var(--amber)',
                    color: '#fff',
                  }}>
                    {item.drift_direction}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  {item.drift_warning} • Pop: {item.popularity_trend_pct}% {item.trend_arrow}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Orders by Type */}
      {metrics.orders_by_type?.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">📦 Orders by Type (30d)</div>
          <div className="card-body">
            <div style={{ display: 'flex', gap: 16 }}>
              {metrics.orders_by_type.map((t, i) => (
                <div key={i} style={{
                  flex: 1, padding: 16, background: 'var(--surface2)',
                  borderRadius: 8, textAlign: 'center',
                }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                    {t.type?.replace('_', ' ')}
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 700 }}>{t.count}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>₹{t.revenue?.toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
