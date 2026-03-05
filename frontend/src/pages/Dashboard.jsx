import { useState, useEffect } from 'react'
import { getDashboardMetrics, getHiddenStars, getRisks, getCategoryBreakdown } from '../api/client'
import MetricCard from '../components/MetricCard'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [hiddenStars, setHiddenStars] = useState([])
  const [riskItems, setRiskItems] = useState([])
  const [categoryData, setCategoryData] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getDashboardMetrics(),
      getHiddenStars(),
      getRisks(),
      getCategoryBreakdown()
    ])
      .then(([metricsData, hiddenStarsData, risksData, categoryBreakdown]) => {
        setMetrics(metricsData)
        setHiddenStars(hiddenStarsData.slice(0, 3) || [])
        setRiskItems(risksData.slice(0, 3) || [])
        setCategoryData(categoryBreakdown || [])
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

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Revenue intelligence overview — all metrics at a glance</p>
      </div>

      {/* KPI Cards */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        <MetricCard
          label="Total Revenue"
          value={`₹${metrics.total_revenue?.toLocaleString() || 0}`}
          color="var(--blue)"
          icon="💰"
        />
        <MetricCard
          label="Avg CM%"
          value={`${metrics.avg_cm_pct || 0}%`}
          color="var(--green)"
          icon="📈"
        />
        <MetricCard
          label="Items At Risk"
          value={metrics.items_at_risk || 0}
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

        {/* Quick View Lists */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header" style={{ color: 'var(--purple)' }}>🔍 Top 3 Hidden Stars</div>
            <div className="card-body">
              {hiddenStars.length === 0 ? <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No hidden stars found.</div> : hiddenStars.map(item => (
                <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ fontSize: 13 }}>{item.name}</span>
                  <span style={{ fontSize: 12, color: 'var(--purple)', fontWeight: 600 }}>CM: {item.cm_percent}%</span>
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
                  <span style={{ fontSize: 12, color: 'var(--red)', fontWeight: 600 }}>CM: {item.cm_percent}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
