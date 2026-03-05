import { useState, useEffect } from 'react'
import { getDashboardMetrics, getHiddenStars, getRisks, getCategoryBreakdown, getTrends } from '../api/client'
import MetricCard from '../components/MetricCard'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import { motion, AnimatePresence } from 'motion/react'
import { StaggerReveal, ScrollReveal, staggerContainer, staggerItem, fadeInUp } from '../utils/animations'
import { formatRupees, formatRupeesShort, formatPct } from '../utils/format'
import { TrendUp, TrendDown, Warning, Star, EyeSlash, ArrowRight } from '@phosphor-icons/react'

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
        setHiddenStars(hiddenStarsData.slice(0, 5) || [])
        setRiskItems(risksData.slice(0, 5) || [])
        setCategoryData(categoryBreakdown || [])
        setTrends(trendsData)
      })
      .catch(err => console.error('Dashboard data load failed:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-12)' }}>
        <div className="grid-3" style={{ marginBottom: 'var(--space-6)' }}>
          {[...Array(6)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 130, animationDelay: `${i * 100}ms` }} />
          ))}
        </div>
        <div className="grid-2">
          <div className="skeleton" style={{ height: 300 }} />
          <div className="skeleton" style={{ height: 300 }} />
        </div>
      </div>
    )
  }

  if (!metrics) {
    return <div className="loading">Failed to load data. Is the backend running?</div>
  }

  const healthBreakdown = metrics.health_score_breakdown || {}
  const driftItems = trends?.quadrant_drift || []
  const peakHours = metrics.peak_hours || []

  // Build alert chips
  const alerts = []
  if (riskItems.length > 0) {
    alerts.push({ type: 'danger', text: `${riskItems.length} underperformers dragging avg margin` })
  }
  if (driftItems.length > 0) {
    alerts.push({ type: 'warning', text: `${driftItems.length} items drifting quadrants` })
  }
  if (hiddenStars.length > 0) {
    alerts.push({ type: 'info', text: `${hiddenStars.length} hidden gems ready to promote` })
  }

  const chartTooltipStyle = {
    backgroundColor: 'var(--bg-surface)',
    borderColor: 'var(--border-subtle)',
    color: 'var(--text-primary)',
    borderRadius: 8,
    fontSize: 12,
    fontFamily: 'var(--font-body)',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      {/* Page Header */}
      <motion.div
        className="page-header"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1>Revenue Overview</h1>
        <p>Last updated — {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</p>
      </motion.div>

      {/* Zone 1: Hero Strip */}
      <motion.div
        style={{
          background: 'linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-base) 100%)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--space-8)',
          marginBottom: 'var(--space-6)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--space-6)',
        }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
      >
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 28, fontWeight: 900, color: 'var(--text-primary)', marginBottom: 4 }}>
            Sizzle Restaurant
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-10)', flexWrap: 'wrap' }}>
          {[
            { label: 'Total Revenue', value: formatRupeesShort(metrics.total_revenue) },
            { label: 'Orders (30d)', value: metrics.total_orders || 0 },
            { label: 'Menu Health', value: metrics.health_score || 0 },
          ].map((item) => (
            <div key={item.label} style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 11, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-secondary)', marginBottom: 4 }}>
                {item.label}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 600, color: 'var(--text-primary)' }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Zone 2: Alert Rail */}
      {alerts.length > 0 && (
        <div style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-6)', overflowX: 'auto', paddingBottom: 4 }}>
          {alerts.map((alert, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.08, duration: 0.3 }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                padding: 'var(--space-2) var(--space-4)',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-full)',
                fontSize: 12,
                color: 'var(--text-secondary)',
                whiteSpace: 'nowrap',
                flexShrink: 0,
              }}
            >
              <span style={{
                width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                background: alert.type === 'danger' ? 'var(--danger)' : alert.type === 'warning' ? 'var(--warning)' : 'var(--info)',
              }} />
              {alert.text}
              <ArrowRight size={12} style={{ color: 'var(--text-muted)' }} />
            </motion.div>
          ))}
        </div>
      )}

      {/* Zone 3: KPI Cards — 3x2 grid */}
      <StaggerReveal className="grid-3" style={{ marginBottom: 'var(--space-6)' }} variants={staggerContainer}>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Menu Health"
            value={metrics.health_score || 0}
            color={metrics.health_score >= 60 ? 'var(--success)' : metrics.health_score >= 40 ? 'var(--warning)' : 'var(--danger)'}
            icon="🏥"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Avg Contribution Margin"
            value={formatPct(metrics.avg_cm_percent)}
            color="var(--success)"
            icon="📈"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Star Items"
            value={metrics.star_count || hiddenStars.length || 0}
            color="var(--success)"
            icon="⭐"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Hidden Gems"
            value={hiddenStars.length || 0}
            color="var(--data-5)"
            icon="💎"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Underperformers"
            value={metrics.items_at_risk_count || 0}
            color="var(--danger)"
            icon="⚠️"
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard
            label="Price Opportunities"
            value={formatRupeesShort(metrics.uplift_potential)}
            color="var(--warning)"
            icon="💡"
          />
        </motion.div>
      </StaggerReveal>

      {/* Health Score Breakdown (collapsible) */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <button
          className="btn btn-ghost"
          onClick={() => setShowHealthBreakdown(!showHealthBreakdown)}
          style={{ fontSize: 12, marginBottom: 'var(--space-3)' }}
        >
          {showHealthBreakdown ? '▾' : '▸'} Health Score Breakdown
        </button>
        <AnimatePresence>
          {showHealthBreakdown && healthBreakdown.components && (
            <motion.div
              className="card"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              <div className="card-body">
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
                  {healthBreakdown.explanation}
                </p>
                <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
                  {healthBreakdown.components.map((c, i) => (
                    <div key={i} style={{
                      flex: '1 1 200px',
                      padding: 'var(--space-4)',
                      background: 'var(--bg-elevated)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-subtle)',
                    }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{c.name}</div>
                      <div style={{
                        fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 600,
                        color: c.score >= 0 ? 'var(--success)' : 'var(--danger)',
                      }}>
                        {c.score > 0 ? '+' : ''}{c.score} <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)' }}>/ {c.max}</span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{c.detail}</div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Zone 4: Intelligence Split — 60/40 */}
      <StaggerReveal style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 'var(--space-6)', marginBottom: 'var(--space-6)' }} variants={staggerContainer}>
        {/* CM% Per Category Chart */}
        <motion.div className="card" variants={staggerItem}>
          <div className="card-header">Average CM% per Category</div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={categoryData} margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                <XAxis dataKey="category" tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'Sora' }} />
                <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'JetBrains Mono' }} />
                <Tooltip cursor={{ fill: 'rgba(30,30,40,0.5)' }} contentStyle={chartTooltipStyle} />
                <Bar dataKey="avg_cm_pct" fill="var(--accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Right column: Hidden Gems + Underperformers */}
        <motion.div variants={staggerItem} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          <div className="card" style={{ flex: 1 }}>
            <div className="card-header" style={{ color: 'var(--data-5)' }}>
              Hidden Gems
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {hiddenStars.length === 0 ? (
                <div style={{ padding: 'var(--space-6)', fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' }}>No hidden gems found.</div>
              ) : hiddenStars.map(item => (
                <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-3) var(--space-6)', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{item.name}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--success)' }}>
                    {formatPct(item.cm_percent || item.margin_pct)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="card" style={{ flex: 1 }}>
            <div className="card-header" style={{ color: 'var(--danger)' }}>
              Underperformers
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {riskItems.length === 0 ? (
                <div style={{ padding: 'var(--space-6)', fontSize: 13, color: 'var(--text-muted)', textAlign: 'center' }}>No items at risk.</div>
              ) : riskItems.slice(0, 5).map(item => (
                <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 'var(--space-3) var(--space-6)', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{item.name}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--danger)' }}>
                    {formatPct(item.cm_percent || item.margin_pct)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </StaggerReveal>

      {/* Peak Hours + Quadrant Drift */}
      <StaggerReveal className="grid-2" style={{ marginBottom: 'var(--space-6)' }} variants={staggerContainer}>
        <motion.div className="card" variants={staggerItem}>
          <div className="card-header">Orders by Hour</div>
          <div className="card-body">
            {peakHours.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', padding: 'var(--space-10)' }}>No hourly data available.</div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={peakHours.sort((a, b) => a.hour - b.hour)} margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                  <XAxis dataKey="label" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'JetBrains Mono' }} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Bar dataKey="order_count" fill="var(--data-5)" radius={[4, 4, 0, 0]} name="Orders" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </motion.div>

        {/* Quadrant Drift Alerts */}
        <motion.div className="card" variants={staggerItem}>
          <div className="card-header" style={{ color: 'var(--warning)' }}>Quadrant Drift Alerts</div>
          <div className="card-body">
            {driftItems.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No significant quadrant shifts detected.</div>
            ) : driftItems.slice(0, 5).map((item, i) => (
              <div key={i} style={{ padding: 'var(--space-2) 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</span>
                  <span className={`tag ${item.drift_direction.includes('dog') ? 'tag-red' : 'tag-amber'}`}>
                    {item.drift_direction}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  {item.drift_warning} • Pop: {item.popularity_trend_pct}% {item.trend_arrow}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </StaggerReveal>

      {/* Orders by Type */}
      {metrics.orders_by_type?.length > 0 && (
        <ScrollReveal variants={fadeInUp}>
          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card-header">Orders by Type (30d)</div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 'var(--space-4)' }}>
                {metrics.orders_by_type.map((t, i) => (
                  <motion.div key={i} style={{
                    flex: 1, padding: 'var(--space-4)', background: 'var(--bg-elevated)',
                    borderRadius: 'var(--radius-md)', textAlign: 'center',
                    border: '1px solid var(--border-subtle)',
                  }}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.1, duration: 0.4 }}
                    whileHover={{ scale: 1.03, transition: { duration: 0.15 } }}
                  >
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {t.type?.replace('_', ' ')}
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 600, color: 'var(--text-primary)', margin: '4px 0' }}>{t.count}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>{formatRupees(t.revenue)}</div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
        </ScrollReveal>
      )}
    </motion.div>
  )
}
