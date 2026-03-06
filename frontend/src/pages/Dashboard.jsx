import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  getDashboardMetrics,
  getHiddenStars,
  getMenuMatrix,
  getPriceRecommendations,
  getRisks,
  getTrends,
  getOpsReports,
  getOpsInventory,
} from '../api/client'
import InfoTooltip from '../components/InfoTooltip'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
} from 'recharts'
import { motion } from 'motion/react'
import { formatRupees, formatRupeesShort, formatPct } from '../utils/format'
import { buildPriceOpportunities, buildUpsellCandidates } from '../utils/revenueInsights'

const CHART_TOOLTIP = {
  backgroundColor: 'var(--bg-overlay)',
  border: '1px solid var(--border-strong)',
  padding: '8px 12px',
  color: '#FFFFFF',
  borderRadius: 8,
  fontSize: 12,
  fontFamily: 'var(--font-body)',
  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
}

function pctChange(previous, current) {
  if (!previous) return current > 0 ? 100 : 0
  return ((current - previous) / previous) * 100
}

function periodTrend(values) {
  if (!values || values.length < 2) return 0
  const midpoint = Math.floor(values.length / 2)
  const prev = values.slice(0, midpoint).reduce((sum, value) => sum + value, 0)
  const curr = values.slice(midpoint).reduce((sum, value) => sum + value, 0)
  return Number(pctChange(prev, curr).toFixed(1))
}

function trendTone(value) {
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return 'flat'
}

function barColorByRank(index, total) {
  if (total <= 1) return 'var(--warning)'
  const ratio = index / (total - 1)
  if (ratio < 0.33) return 'var(--success)'
  if (ratio < 0.66) return 'var(--warning)'
  return 'var(--danger)'
}

function Sparkline({ data, color }) {
  return (
    <ResponsiveContainer width="100%" height={28}>
      <LineChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 0 }}>
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [metrics, setMetrics] = useState(null)
  const [trends, setTrends] = useState(null)
  const [reports, setReports] = useState(null)
  const [loading, setLoading] = useState(true)
  const [secondaryLoaded, setSecondaryLoaded] = useState(false)
  const [hiddenStars, setHiddenStars] = useState([])
  const [riskItems, setRiskItems] = useState([])
  const [lowStock, setLowStock] = useState([])
  const [menuMatrixItems, setMenuMatrixItems] = useState([])
  const [priceRecommendations, setPriceRecommendations] = useState([])
  const [secondaryErrors, setSecondaryErrors] = useState([])
  const [selectedChip, setSelectedChip] = useState(null)

  useEffect(() => {
    let active = true

    Promise.all([getDashboardMetrics(), getOpsReports(30)])
      .then(([dashboardData, reportData]) => {
        if (!active) return
        setMetrics(dashboardData)
        setReports(reportData)
      })
      .catch((error) => {
        console.error('Dashboard load failed:', error)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    const errors = []
    const loadSafe = (label, promise, fallback) =>
      promise.catch((error) => {
        errors.push(label)
        console.error(`${label} load failed:`, error)
        return fallback
      })

    Promise.all([
      loadSafe('Hidden Stars', getHiddenStars(), { items: [] }),
      loadSafe('Risks', getRisks(), { items: [] }),
      loadSafe('Trends', getTrends(), null),
      loadSafe('Inventory', getOpsInventory(30), { low_stock: [] }),
      loadSafe('Menu Matrix', getMenuMatrix(), { items: [] }),
      loadSafe('Price Recommendations', getPriceRecommendations(), { recommendations: [] }),
    ]).then(([hs, risks, trendData, inventory, menuMatrix, priceData]) => {
      if (!active) return
      setHiddenStars((hs.items || []).slice(0, 6))
      setRiskItems((risks.items || []).slice(0, 6))
      setTrends(trendData)
      setLowStock((inventory.low_stock || []).slice(0, 6))
      setMenuMatrixItems((menuMatrix?.items || []))
      setPriceRecommendations((priceData?.recommendations || []))
      setSecondaryErrors(errors)
      setSecondaryLoaded(true)
    })

    return () => {
      active = false
    }
  }, [])

  const dailySeries = reports?.daily || []
  const revenueSeries = useMemo(
    () => dailySeries.map((row) => ({ day: row.date?.slice(5) || '', value: row.revenue || 0 })),
    [dailySeries],
  )
  const orderSeries = useMemo(
    () => dailySeries.map((row) => ({ day: row.date?.slice(5) || '', value: row.orders || 0 })),
    [dailySeries],
  )
  const aovSeries = useMemo(
    () => dailySeries.map((row) => ({ day: row.date?.slice(5) || '', value: row.orders ? row.revenue / row.orders : 0 })),
    [dailySeries],
  )

  const todayRow = dailySeries.find((row) => row.is_today)
  const todayRevenue = todayRow?.revenue || 0
  const todayOrders = todayRow?.orders || 0
  const todayAov = todayOrders > 0 ? todayRevenue / todayOrders : 0

  const revenueTrend = periodTrend(revenueSeries.map((point) => point.value))
  const ordersTrend = periodTrend(orderSeries.map((point) => point.value))
  const aovTrend = periodTrend(aovSeries.map((point) => point.value))
  const upsellItems = useMemo(() => (
    buildUpsellCandidates({
      items: menuMatrixItems,
      trends,
      currentOrderItems: [],
      limit: 6,
    })
  ), [menuMatrixItems, trends])

  const priceInsight = useMemo(() => (
    buildPriceOpportunities({
      items: menuMatrixItems,
      combos: [],
      apiRecommendations: priceRecommendations,
      totalOrders: metrics?.total_orders || 0,
    })
  ), [menuMatrixItems, priceRecommendations, metrics])

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-8)' }}>
        <div className="skeleton" style={{ height: 88, marginBottom: 'var(--space-6)' }} />
        <div className="grid-2">
          <div className="skeleton" style={{ height: 280 }} />
          <div className="skeleton" style={{ height: 280 }} />
        </div>
      </div>
    )
  }

  if (!metrics) {
    return <div className="loading">Failed to load dashboard data. Ensure the backend is running.</div>
  }

  const topItemsByRevenue = [...(trends?.item_trends || [])]
    .sort((a, b) => (a.revenue_last_30d || 0) - (b.revenue_last_30d || 0))
    .slice(-8)

  const hourlyOrders = [...(metrics.peak_hours || [])]
    .map((row) => ({ label: row.label || `${row.hour}:00`, orders: row.order_count || 0 }))

  const driftItems = (trends?.quadrant_drift || []).slice(0, 5)

  const alertChips = [
    { label: `${riskItems.length} underperformers`, tone: 'danger', target: 'underperformers' },
    { label: `${hiddenStars.length} hidden gems`, tone: 'success', target: 'hidden-gems' },
    { label: `${lowStock.length} low stock alerts`, tone: 'warning', target: 'low-stock' },
    { label: `${driftItems.length} quadrant drifts`, tone: 'info', target: 'quadrant-drift' },
  ]

  const kpiChips = [
    {
      title: "Today's Revenue",
      value: formatRupeesShort(todayRevenue),
      trend: revenueTrend,
      sparkline: revenueSeries,
    },
    {
      title: "Today's Orders",
      value: (todayOrders).toLocaleString('en-IN'),
      trend: ordersTrend,
      sparkline: orderSeries,
    },
    {
      title: 'Avg Order Value',
      value: formatRupees(todayAov),
      trend: aovTrend,
      sparkline: aovSeries,
    },
    {
      title: 'Menu Health',
      value: `${metrics.health_score || 0}/100`,
      trend: Number((hiddenStars.length - riskItems.length).toFixed(1)),
      sparkline: revenueSeries,
    },
  ]

  return (
    <motion.div
      className="app-page dash-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <section className="dash-header-compact">
        <div className="dash-header-main">
          <h1 className="dash-title">Dashboard Overview</h1>
          <p className="dash-subtitle">
            <span className="dash-live-dot" />
            Last updated {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
          </p>
        </div>

        <div className="dash-kpi-chip-row">
          {kpiChips.map((chip) => {
            const tone = trendTone(chip.trend)
            const isSelected = selectedChip === chip.title
            return (
              <motion.div
                key={chip.title}
                className={`dash-kpi-chip ${isSelected ? 'dash-kpi-chip--selected' : ''}`}
                onClick={() => setSelectedChip(isSelected ? null : chip.title)}
                whileTap={{ scale: 0.98 }}
                animate={isSelected ? { scale: 1.02, y: -4 } : { scale: 1, y: 0 }}
              >
                <div className="dash-kpi-chip-head">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span className="dash-kpi-chip-label">{chip.title}</span>
                    {chip.title === 'Menu Health' && (
                      <InfoTooltip
                        title="Menu Health Breakdown"
                        explanation={metrics.health_score_breakdown?.explanation}
                        components={metrics.health_score_breakdown?.components}
                      />
                    )}
                  </div>
                  <span className={`dash-kpi-trend dash-kpi-trend--${tone}`}>
                    {chip.trend > 0 ? '+' : ''}{chip.trend}%
                  </span>
                </div>
                <div className="dash-kpi-chip-value">{chip.value}</div>
                <div className="dash-kpi-sparkline">
                  <Sparkline data={chip.sparkline} color={tone === 'up' ? '#2A7A50' : tone === 'down' ? '#8C2A2A' : '#9E9AAF'} />
                </div>
              </motion.div>
            )
          })}
        </div>
      </section>

      {secondaryLoaded && secondaryErrors.length > 0 && (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="card-body" style={{ color: 'var(--warning)', fontSize: 12 }}>
            Some sections loaded partially: {secondaryErrors.join(', ')}
          </div>
        </div>
      )}

      <section className="dash-alert-strip" aria-label="AI insight alerts">
        {alertChips.map((chip) => {
          const isSelected = selectedChip === chip.target
          return (
            <motion.div
              key={chip.label}
              className={`dash-alert-chip dash-alert-chip--${chip.tone} ${isSelected ? 'dash-alert-chip--selected' : ''}`}
              style={{ cursor: 'pointer' }}
              onClick={() => {
                setSelectedChip(isSelected ? null : chip.target)
                document.getElementById(chip.target)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }}
              animate={isSelected ? { scale: 1.05 } : { scale: 1 }}
              whileTap={{ scale: 0.95 }}
            >
              {chip.label}
            </motion.div>
          )
        })}
      </section>

      <section className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card-header">AI Upsell Opportunities</div>
        <div className="card-body" style={{ overflowX: 'auto' }}>
          {secondaryLoaded ? (
            upsellItems.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                No strong upsell candidates yet. Add more order history to improve candidate ranking.
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 'var(--space-3)', minWidth: 'max-content' }}>
                {upsellItems.slice(0, 6).map((item) => (
                  <div
                    key={item.item_id}
                    className="card"
                    style={{ minWidth: 260, borderColor: 'var(--border-subtle)' }}
                  >
                    <div className="card-body">
                      <div style={{ fontWeight: 700, marginBottom: 6 }}>{item.name}</div>
                      <div style={{ color: 'var(--success)', fontWeight: 700, marginBottom: 8 }}>
                        Contribution Margin {formatPct(item.cm_percent)}
                      </div>
                      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                        {item.reason}
                      </p>
                      <button
                        className="btn btn-ghost"
                        style={{ fontSize: 12, padding: 0 }}
                        onClick={() => navigate(`/dashboard/menu-analysis?item=${item.item_id}`)}
                      >
                        View Item
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
              {Array.from({ length: 3 }).map((_, idx) => (
                <div key={idx} className="skeleton" style={{ height: 130 }} />
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Price Opportunities</span>
          <Link to="/dashboard/menu-analysis?tab=price-opportunities" className="btn btn-ghost" style={{ fontSize: 12 }}>
            Review Suggestions
          </Link>
        </div>
        <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Identified Opportunities</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--accent)' }}>
              {priceInsight.opportunities.length}
            </div>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 420 }}>
            {priceInsight.insufficientData && priceInsight.opportunities.length === 0
              ? 'Not enough order history to generate price recommendations yet.'
              : 'Recommendations are based on BCG quadrant behavior, margin signals, and bundle opportunities.'}
          </div>
        </div>
      </section>

      <section className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card">
          <div className="card-header">Revenue Trend (30D)</div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={revenueSeries} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} tickFormatter={(v) => formatRupeesShort(v)} />
                <Tooltip contentStyle={CHART_TOOLTIP} itemStyle={{ color: '#fff' }} labelStyle={{ color: '#fff' }} formatter={(value) => formatRupees(value)} />
                <Line type="monotone" dataKey="value" stroke="#E85D2A" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Orders by Hour</div>
          <div className="card-body">
            {hourlyOrders.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No hourly order data available.</div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={hourlyOrders} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                  <XAxis dataKey="label" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                  <Tooltip contentStyle={CHART_TOOLTIP} itemStyle={{ color: '#fff' }} labelStyle={{ color: '#fff' }} cursor={false} formatter={(value) => [`${value} orders`, 'Orders']} labelFormatter={() => ''} />
                  <Bar dataKey="orders" radius={[6, 6, 0, 0]} background={{ fill: 'rgba(255, 255, 255, 0.05)', radius: [6, 6, 0, 0] }}>
                    {hourlyOrders.map((_, index) => (
                      <Cell key={index} fill={barColorByRank(index, hourlyOrders.length)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </section>

      <section className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card">
          <div className="card-header">Top Menu Items by Revenue</div>
          <div className="card-body">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={topItemsByRevenue} layout="vertical" margin={{ top: 10, right: 12, left: 12, bottom: 10 }}>
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" width={120} tick={{ fill: 'var(--text-primary)', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={CHART_TOOLTIP} itemStyle={{ color: '#fff' }} labelStyle={{ color: '#fff' }} formatter={(value) => formatRupees(value)} cursor={{ fill: 'var(--bg-overlay)' }} />
                <Bar dataKey="revenue_last_30d" radius={[0, 6, 6, 0]} background={{ fill: 'rgba(255, 255, 255, 0.05)', radius: [0, 6, 6, 0] }}>
                  {topItemsByRevenue.map((_, index) => (
                    <Cell key={index} fill={barColorByRank(index, topItemsByRevenue.length)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card" id="low-stock">
          <div className="card-header">Low Stock Alerts</div>
          <div className="card-body">
            {lowStock.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No critical low-stock ingredients.</div>
            ) : (
              <div className="dash-low-stock-list">
                {lowStock.map((item) => (
                  <div key={item.ingredient_id} className="dash-low-stock-item">
                    <div>
                      <div className="dash-low-stock-name">{item.name}</div>
                      <div className="dash-low-stock-meta">{item.current_stock} {item.unit} left • Reorder at {item.reorder_level}</div>
                    </div>
                    <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => navigate('/dashboard/inventory')}>Reorder</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card" id="hidden-gems">
          <div className="card-header">Hidden Gems</div>
          <div className="dash-list-header">
            <span>Item</span>
            <span>CM%</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {hiddenStars.length === 0 ? (
              <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)', fontSize: 13 }}>No hidden gems found.</div>
            ) : hiddenStars.map((item) => (
              <div key={item.item_id} className="dash-list-row">
                <span>{item.name}</span>
                <span style={{ color: 'var(--success)', fontFamily: 'var(--font-mono)' }}>{formatPct(item.cm_percent || item.margin_pct)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card" id="underperformers">
          <div className="card-header">Underperformers</div>
          <div className="dash-list-header">
            <span>Item</span>
            <span>CM%</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {riskItems.length === 0 ? (
              <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)', fontSize: 13 }}>No items at risk.</div>
            ) : riskItems.map((item) => (
              <div key={item.item_id} className="dash-list-row">
                <span>{item.name}</span>
                <span style={{ color: 'var(--danger)', fontFamily: 'var(--font-mono)' }}>{formatPct(item.cm_percent || item.margin_pct)}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="card" id="quadrant-drift" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card-header">Quadrant Drift Alerts</div>
        <div className="card-body">
          {driftItems.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No significant drift alerts at the moment.</div>
          ) : (
            <div className="dash-drift-grid">
              {driftItems.map((item) => (
                <div key={item.item_id} className="dash-drift-card">
                  <div className="dash-drift-top">
                    <strong>{item.name}</strong>
                    <span className="dash-drift-badge">{item.drift_direction}</span>
                  </div>
                  <p>{item.drift_warning}</p>
                  <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => navigate(`/dashboard/menu-analysis?item=${item.item_id}`)}>Promote This Item</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </motion.div>
  )
}
