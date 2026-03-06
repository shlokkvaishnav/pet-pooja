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
import { useTranslation } from '../context/LanguageContext'
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
  const { t } = useTranslation()
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
    const controller = new AbortController()
    const { signal } = controller

    Promise.all([getDashboardMetrics({ signal }), getOpsReports(30, { signal })])
      .then(([dashboardData, reportData]) => {
        if (signal.aborted) return
        setMetrics(dashboardData)
        setReports(reportData)
      })
      .catch((error) => {
        if (signal.aborted) return
        console.error('Dashboard load failed:', error)
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })

    const errors = []
    const loadSafe = (label, promise, fallback) =>
      promise.catch((error) => {
        if (signal.aborted) return fallback
        errors.push(label)
        console.error(`${label} load failed:`, error)
        return fallback
      })

    Promise.all([
      loadSafe('Hidden Stars', getHiddenStars({ signal }), { items: [] }),
      loadSafe('Risks', getRisks({ signal }), { items: [] }),
      loadSafe('Trends', getTrends({ signal }), null),
      loadSafe('Inventory', getOpsInventory(30, { signal }), { low_stock: [] }),
      loadSafe('Menu Matrix', getMenuMatrix({ signal }), { items: [] }),
      loadSafe('Price Recommendations', getPriceRecommendations({ signal }), { recommendations: [] }),
    ]).then(([hs, risks, trendData, inventory, menuMatrix, priceData]) => {
      if (signal.aborted) return
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
      controller.abort()
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
    return <div className="loading">{t('dash_failed_load')}</div>
  }

  const topItemsByRevenue = [...(trends?.item_trends || [])]
    .sort((a, b) => (a.revenue_last_30d || 0) - (b.revenue_last_30d || 0))
    .slice(-8)

  const hourlyOrders = [...(metrics.peak_hours || [])]
    .map((row) => ({ label: row.label || `${row.hour}:00`, orders: row.order_count || 0 }))

  const driftItems = (trends?.quadrant_drift || []).slice(0, 5)

  const alertChips = [
    { label: `${riskItems.length} ${t('dash_underperformers')}`, tone: riskItems.length > 0 ? 'danger' : 'neutral', target: 'underperformers' },
    { label: `${hiddenStars.length} ${t('dash_hidden_gems')}`, tone: hiddenStars.length > 0 ? 'success' : 'neutral', target: 'hidden-gems' },
    { label: `${lowStock.length} ${t('dash_low_stock_alerts')}`, tone: lowStock.length > 0 ? 'warning' : 'neutral', target: 'low-stock' },
    { label: `${driftItems.length} ${t('dash_quadrant_drifts')}`, tone: driftItems.length > 0 ? 'info' : 'neutral', target: 'quadrant-drift' },
  ]

  const kpiChips = [
    {
      title: t('dash_today_revenue'),
      value: formatRupeesShort(todayRevenue),
      trend: revenueTrend,
      sparkline: revenueSeries,
    },
    {
      title: t('dash_today_orders'),
      value: (todayOrders).toLocaleString('en-IN'),
      trend: ordersTrend,
      sparkline: orderSeries,
    },
    {
      title: t('dash_avg_order_value'),
      value: formatRupees(todayAov),
      trend: aovTrend,
      sparkline: aovSeries,
    },
    {
      title: t('dash_menu_health'),
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
          <h1 className="dash-title">{t('dash_title')}</h1>
          <p className="dash-subtitle">
            <span className="dash-live-dot" />
            {t('dash_last_updated')} {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
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
                whileHover={{ scale: 1.03, y: -4 }}
                whileTap={{ scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              >
                <div className="dash-kpi-chip-head">
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span className="dash-kpi-chip-label">{chip.title}</span>
                    {chip.title === t('dash_menu_health') && (
                      <InfoTooltip
                        title={t('dash_menu_health_breakdown')}
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
            {t('dash_partial_load')} {secondaryErrors.join(', ')}
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
        <div className="card-header">{t('dash_upsell')}</div>
        <div className="card-body" style={{ overflowX: 'auto' }}>
          {secondaryLoaded ? (
            upsellItems.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                {t('dash_no_upsell')}
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
                        {t('dash_contribution_margin')} {formatPct(item.cm_percent)}
                      </div>
                      <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                        {item.reason}
                      </p>
                      <button
                        className="btn btn-ghost"
                        style={{ fontSize: 12, padding: 0 }}
                        onClick={() => navigate(`/dashboard/menu-analysis?item=${item.item_id}`)}
                      >
                        {t('dash_view_item')}
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
          <span>{t('dash_price_opps')}</span>
          <Link to="/dashboard/menu-analysis?tab=price-opportunities" className="btn btn-ghost" style={{ fontSize: 12 }}>
            {t('dash_review_suggestions')}
          </Link>
        </div>
        <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{t('dash_identified_opps')}</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--accent)' }}>
              {priceInsight.opportunities.length}
            </div>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 420 }}>
            {priceInsight.insufficientData && priceInsight.opportunities.length === 0
              ? t('dash_no_price_recs')
              : 'Recommendations are based on BCG quadrant behavior, margin signals, and bundle opportunities.'}
          </div>
        </div>
      </section>

      <section className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card">
          <div className="card-header">{t('dash_revenue_trend')}</div>
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
          <div className="card-header">{t('dash_orders_by_hour')}</div>
          <div className="card-body">
            {hourlyOrders.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t('dash_no_hourly')}</div>
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
          <div className="card-header">{t('dash_top_items')}</div>
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
          <div className="card-header">{t('dash_low_stock')}</div>
          <div className="card-body">
            {lowStock.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t('dash_no_low_stock')}</div>
            ) : (
              <div className="dash-low-stock-list">
                {lowStock.map((item) => (
                  <div key={item.ingredient_id} className="dash-low-stock-item">
                    <div>
                      <div className="dash-low-stock-name">{item.name}</div>
                      <div className="dash-low-stock-meta">{item.current_stock} {item.unit} left • Reorder at {item.reorder_level}</div>
                    </div>
                    <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => navigate('/dashboard/inventory')}>{t('dash_reorder')}</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card" id="hidden-gems">
          <div className="card-header">{t('dash_hidden_gems_section')}</div>
          <div className="dash-list-header">
            <span>{t('dash_item')}</span>
            <span>{t('dash_cm_pct')}</span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {hiddenStars.length === 0 ? (
              <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)', fontSize: 13 }}>{t('dash_no_hidden_gems')}</div>
            ) : hiddenStars.map((item) => (
              <div key={item.item_id} className="dash-list-row">
                <span>{item.name}</span>
                <span style={{ color: 'var(--success)', fontFamily: 'var(--font-mono)' }}>{formatPct(item.cm_percent || item.margin_pct)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card" id="underperformers">
          <div className="card-header">{t('dash_underperformers_section')}</div>
          <div className="dash-list-header">
            <span>{t('dash_item')}</span>
            <span>{t('dash_cm_pct')}</span>
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
