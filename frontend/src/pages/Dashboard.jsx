import { useState, useEffect } from 'react'
import {
  getDashboardMetrics,
  getHiddenStars,
  getRisks,
  getCategoryBreakdown,
  getTrends,
  getWowMom,
  getPriceElasticity,
  getCannibalization,
  getPriceSensitivity,
  getWasteAnalysis,
  getCustomerReturns,
  getMenuComplexity,
  getOperationalMetrics,
} from '../api/client'
import MetricCard from '../components/MetricCard'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend, CartesianGrid, Area, AreaChart,
} from 'recharts'
import { motion, AnimatePresence } from 'motion/react'
import { StaggerReveal, ScrollReveal, staggerContainer, staggerItem, fadeInUp } from '../utils/animations'
import { formatRupees, formatRupeesShort, formatPct } from '../utils/format'
import { TrendUp, TrendDown, Warning, Star, EyeSlash, ArrowRight } from '@phosphor-icons/react'

const CHART_COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
const TOOLTIP_STYLE = { backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border-subtle)', color: 'var(--text-primary)', fontSize: 12, fontFamily: 'var(--font-body)' }
const TICK_STYLE = { fill: 'var(--text-secondary)', fontSize: 11 }

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [hiddenStars, setHiddenStars] = useState([])
  const [riskItems, setRiskItems] = useState([])
  const [categoryData, setCategoryData] = useState([])
  const [trends, setTrends] = useState(null)
  const [wowMom, setWowMom] = useState([])
  const [elasticity, setElasticity] = useState([])
  const [cannibalization, setCannibalization] = useState([])
  const [priceSensitivity, setPriceSensitivity] = useState([])
  const [waste, setWaste] = useState(null)
  const [customerReturns, setCustomerReturns] = useState(null)
  const [menuComplexity, setMenuComplexity] = useState([])
  const [showHealthBreakdown, setShowHealthBreakdown] = useState(false)
  const [secondaryLoaded, setSecondaryLoaded] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    // Load critical metrics first so the page can render quickly.
    getDashboardMetrics()
      .then((m) => {
        if (!active) return
        setMetrics(m)
      })
      .catch(err => {
        console.error('Dashboard load failed:', err)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    // Load secondary datasets in the background.
    Promise.all([
      getHiddenStars().catch(() => ({ items: [] })),
      getRisks().catch(() => ({ items: [] })),
      getCategoryBreakdown().catch(() => ({ categories: [] })),
      getTrends().catch(() => null),
      getWowMom().catch(() => ({ items: [] })),
      getPriceElasticity().catch(() => ({ items: [] })),
      getCannibalization().catch(() => ({ items: [] })),
      getPriceSensitivity().catch(() => ({ items: [] })),
      getWasteAnalysis().catch(() => null),
      getCustomerReturns().catch(() => null),
      getMenuComplexity().catch(() => ({ categories: [] })),
    ])
      .then(([hs, ri, cb, tr, wm, el, cn, ps, wa, cr, mc]) => {
        if (!active) return
        setHiddenStars((hs.items || hs || []).slice(0, 5))
        setRiskItems((ri.items || ri || []).slice(0, 5))
        setCategoryData(cb.categories || cb || [])
        setTrends(tr)
        setWowMom((wm.items || []).slice(0, 10))
        setElasticity((el.items || []).slice(0, 10))
        setCannibalization((cn.items || []).slice(0, 8))
        setPriceSensitivity((ps.items || []).slice(0, 8))
        setWaste(wa)
        setCustomerReturns(cr)
        setMenuComplexity(mc.categories || [])
      })
      .finally(() => {
        if (active) setSecondaryLoaded(true)
      })

    return () => {
      active = false
    }
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
  const seasonalPatterns = trends?.seasonal_patterns || []

  const categoryPieData = categoryData.slice(0, 6).map((c, i) => ({
    name: c.category_name || c.category,
    value: c.total_revenue || 0,
    fill: CHART_COLORS[i % CHART_COLORS.length],
  }))

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
      className="app-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <motion.div
        className="app-hero"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
      >
        <div>
          <div className="app-hero-eyebrow">Overview</div>
          <h1 className="app-hero-title">Revenue Overview</h1>
          <p className="app-hero-sub">
            Last updated - {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>
        <div className="app-hero-metrics">
          {[
            { label: 'Total Revenue', value: formatRupeesShort(metrics.total_revenue) },
            { label: 'Orders (30d)', value: metrics.total_orders || 0 },
            { label: 'Menu Health', value: metrics.health_score || 0 },
          ].map((item) => (
            <div key={item.label} className="app-kpi">
              <div className="app-kpi-label">{item.label}</div>
              <div className="app-kpi-value">{item.value}</div>
            </div>
          ))}
        </div>
      </motion.div>

      {!secondaryLoaded && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="card-body" style={{ fontSize: 12, color: 'var(--text-muted)', padding: 'var(--space-3) var(--space-5)' }}>
            Loading advanced insights...
          </div>
        </div>
      )}

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

      {/* Zone 3: KPI Cards */}
      <StaggerReveal className="grid-3" style={{ marginBottom: 'var(--space-6)' }} variants={staggerContainer}>
        <motion.div variants={staggerItem}>
          <MetricCard label="Menu Health" value={metrics.health_score || 0} color={metrics.health_score >= 60 ? 'var(--success)' : metrics.health_score >= 40 ? 'var(--warning)' : 'var(--danger)'} icon="" />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard label="Avg Contribution Margin" value={formatPct(metrics.avg_cm_percent)} color="var(--success)" icon="" />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard label="Star Items" value={metrics.stars_count || hiddenStars.length || 0} color="var(--success)" icon="" />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard label="Hidden Gems" value={hiddenStars.length || 0} color="var(--data-5)" icon="" />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard label="Underperformers" value={metrics.items_at_risk_count || 0} color="var(--danger)" icon="" />
        </motion.div>
        <motion.div variants={staggerItem}>
          <MetricCard label="Price Opportunities" value={formatRupeesShort(metrics.uplift_potential)} color="var(--warning)" icon="" />
        </motion.div>
      </StaggerReveal>

      {/* Health Score Breakdown (collapsible) */}
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <button className="btn btn-ghost" onClick={() => setShowHealthBreakdown(!showHealthBreakdown)} style={{ fontSize: 12, marginBottom: 'var(--space-3)' }}>
          {showHealthBreakdown ? '' : ''} Health Score Breakdown
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
                      flex: '1 1 200px', padding: 'var(--space-4)', background: 'var(--bg-elevated)',
                      borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)',
                    }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{c.name}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 600, color: c.score >= 0 ? 'var(--success)' : 'var(--danger)' }}>
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

        <motion.div variants={staggerItem} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
          <div className="card" style={{ flex: 1 }}>
            <div className="card-header" style={{ color: 'var(--data-5)' }}>Hidden Gems</div>
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
            <div className="card-header" style={{ color: 'var(--danger)' }}>Underperformers</div>
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

        <motion.div className="card" variants={staggerItem}>
          <div className="card-header" style={{ color: 'var(--warning)' }}>Quadrant Drift Alerts</div>
          <div className="card-body">
            {driftItems.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>No significant quadrant shifts detected.</div>
            ) : driftItems.slice(0, 5).map((item, i) => (
              <div key={i} style={{ padding: 'var(--space-2) 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</span>
                  <span className={`tag ${item.drift_direction?.includes('dog') ? 'tag-red' : 'tag-amber'}`}>
                    {item.drift_direction}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  {item.drift_warning}  Pop: {item.popularity_trend_pct}% {item.trend_arrow}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </StaggerReveal>

      {/* Revenue by Category Pie */}
      <StaggerReveal className="grid-2" style={{ marginBottom: 'var(--space-6)' }} variants={staggerContainer}>
        <motion.div className="card" variants={staggerItem}>
          <div className="card-header">Revenue by Category</div>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'center' }}>
            {categoryPieData.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--text-muted)', padding: 'var(--space-10)' }}>No data.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie data={categoryPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                    {categoryPieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={chartTooltipStyle} formatter={(v) => formatRupees(v)} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </motion.div>

        {metrics.orders_by_type?.length > 0 && (
          <motion.div className="card" variants={staggerItem}>
            <div className="card-header">Orders by Type (30d)</div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
                {metrics.orders_by_type.map((t, i) => (
                  <motion.div key={i} style={{
                    flex: '1 1 80px', padding: 'var(--space-4)', background: 'var(--bg-elevated)',
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
          </motion.div>
        )}
      </StaggerReveal>

      {/* WoW / MoM Revenue Changes */}
      {wowMom.length > 0 && (
        <ScrollReveal variants={fadeInUp}>
          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card-header">Week-over-Week / Month-over-Month Revenue Changes</div>
            <div className="card-body">
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>WoW Change</th>
                      <th>MoM Change</th>
                      <th>This Week Revenue</th>
                      <th>Last Week Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wowMom.map((item, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{item.name}</td>
                        <td style={{ color: (item.wow_change_pct || 0) >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                          {(item.wow_change_pct || 0) > 0 ? '+' : ''}{item.wow_change_pct?.toFixed(1) || '—'}%
                        </td>
                        <td style={{ color: (item.mom_change_pct || 0) >= 0 ? 'var(--success)' : 'var(--danger)', fontWeight: 600 }}>
                          {(item.mom_change_pct || 0) > 0 ? '+' : ''}{item.mom_change_pct?.toFixed(1) || '—'}%
                        </td>
                        <td>{formatRupees(item.this_week_revenue)}</td>
                        <td>{formatRupees(item.last_week_revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </ScrollReveal>
      )}

      {/* Price Elasticity */}
      {elasticity.length > 0 && (
        <ScrollReveal variants={fadeInUp}>
          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card-header">Price Elasticity Estimates</div>
            <div className="card-body">
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-3)' }}>Items where price changes affected demand volume.</p>
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Price Change</th>
                      <th>Volume Change</th>
                      <th>Elasticity</th>
                      <th>Classification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {elasticity.map((item, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: 600 }}>{item.name}</td>
                        <td>{item.price_change_pct?.toFixed(1) || '—'}%</td>
                        <td style={{ color: (item.volume_change_pct || 0) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                          {item.volume_change_pct?.toFixed(1) || '—'}%
                        </td>
                        <td>{item.elasticity?.toFixed(2) || '—'}</td>
                        <td>
                          <span className={`tag tag-${item.classification === 'elastic' ? 'red' : item.classification === 'inelastic' ? 'green' : 'blue'}`}>
                            {item.classification || '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </ScrollReveal>
      )}

      {/* Cannibalization + Price Sensitivity */}
      <div className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        {cannibalization.length > 0 && (
          <div className="card">
            <div className="card-header" style={{ color: 'var(--danger)' }}>Cannibalization Alerts</div>
            <div className="card-body">
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-3)' }}>New items that may be eating into existing sales.</p>
              {cannibalization.map((item, i) => (
                <div key={i} style={{ padding: 'var(--space-3) 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.new_item || item.name}</span>
                    <span style={{ fontSize: 11, color: 'var(--danger)', fontWeight: 600 }}>
                      {item.cannibalization_pct?.toFixed(0) || item.overlap_pct?.toFixed(0) || '—'}% overlap
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    Affected: {item.affected_item || item.victim || '—'}  {item.recommendation || ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {priceSensitivity.length > 0 && (
          <div className="card">
            <div className="card-header" style={{ color: 'var(--warning)' }}>Price Sensitivity — Plowhorse Items</div>
            <div className="card-body">
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-3)' }}>High-volume, low-margin items that could absorb a price increase.</p>
              {priceSensitivity.map((item, i) => (
                <div key={i} style={{ padding: 'var(--space-3) 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--success)' }}>
                      +{formatRupees(item.projected_revenue_gain || item.revenue_impact)}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    Current: {formatRupees(item.current_price)}  Suggested: {formatRupees(item.suggested_price || item.recommended_price)} | {item.recommendation || ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Waste & Voids + Customer Returns */}
      <div className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        {waste && (
          <div className="card">
            <div className="card-header" style={{ color: 'var(--danger)' }}>Waste & Void Analysis (30d)</div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Total Waste Cost</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--danger)' }}>{formatRupees(waste.total_waste_cost)}</div>
                </div>
                <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Void Rate</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--warning)' }}>{waste.void_rate_pct?.toFixed(1) || 0}%</div>
                </div>
              </div>
              {waste.top_voided_items?.length > 0 && (
                <>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-2)', fontWeight: 600 }}>Top Voided Items</div>
                  {waste.top_voided_items.slice(0, 5).map((item, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--space-2) 0', fontSize: 13, borderBottom: '1px solid var(--border-subtle)' }}>
                      <span>{item.name}</span>
                      <span style={{ color: 'var(--danger)', fontWeight: 600 }}>{item.void_count || item.count} voids</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        )}

        {customerReturns && (
          <div className="card">
            <div className="card-header" style={{ color: 'var(--success)' }}>Customer Return Rates</div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Repeat Rate</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--success)' }}>{customerReturns.repeat_rate_pct?.toFixed(1) || 0}%</div>
                </div>
                <div style={{ padding: 'var(--space-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Unique Tables</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>{customerReturns.unique_tables || customerReturns.unique_customers || 0}</div>
                </div>
              </div>
              {customerReturns.top_returning_tables?.length > 0 && (
                <>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-2)', fontWeight: 600 }}>Most Frequent Tables</div>
                  {customerReturns.top_returning_tables.slice(0, 5).map((t, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--space-2) 0', fontSize: 13, borderBottom: '1px solid var(--border-subtle)' }}>
                      <span>{t.table_id || t.table || `Table ${i + 1}`}</span>
                      <span style={{ fontWeight: 600 }}>{t.visit_count || t.visits} visits</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Menu Complexity */}
      {menuComplexity.length > 0 && (
        <ScrollReveal variants={fadeInUp}>
          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card-header">Menu Complexity by Category</div>
            <div className="card-body">
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 'var(--space-3)' }}>Categories with more than 7 items may suffer from decision fatigue.</p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
                {menuComplexity.map((cat, i) => (
                  <div key={i} style={{
                    padding: 'var(--space-4)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)',
                    border: `1px solid ${cat.item_count > 7 || cat.alert ? 'var(--warning)' : 'var(--border-subtle)'}`,
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, color: 'var(--text-primary)' }}>{cat.category_name || cat.name}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>{cat.item_count || cat.count}</div>
                    <div style={{ fontSize: 11, color: (cat.item_count > 7 || cat.alert) ? 'var(--warning)' : 'var(--text-muted)' }}>
                      {(cat.item_count > 7 || cat.alert) ? ' Consider trimming' : 'Optimal range'}
                    </div>
                    {cat.complexity_score != null && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Score: {cat.complexity_score}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </ScrollReveal>
      )}

      {/* Seasonal Patterns */}
      {seasonalPatterns.length > 0 && (
        <ScrollReveal variants={fadeInUp}>
          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card-header">Seasonal / Day-of-Week Patterns</div>
            <div className="card-body">
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={seasonalPatterns} margin={{ top: 10, right: 10, bottom: 20, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                  <XAxis dataKey="day" tick={TICK_STYLE} />
                  <YAxis tick={TICK_STYLE} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Bar dataKey="avg_revenue" fill="var(--warning)" radius={[4, 4, 0, 0]} name="Avg Revenue" />
                  <Bar dataKey="avg_orders" fill="var(--info)" radius={[4, 4, 0, 0]} name="Avg Orders" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </ScrollReveal>
      )}
    </motion.div>
  )
}
