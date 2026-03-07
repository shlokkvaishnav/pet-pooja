import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getCombos, getDashboardMetrics, getMenuMatrix, getPriceRecommendations, getTrends, getCategoryBreakdown } from '../api/client'
import MenuMatrix from '../components/MenuMatrix'
import ItemTable from '../components/ItemTable'
import { motion } from 'motion/react'
import { ScrollReveal, fadeInUp } from '../utils/animations'
import { buildPriceOpportunities } from '../utils/revenueInsights'
import { formatRupees, formatPct } from '../utils/format'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts'
import { useTranslation } from '../context/LanguageContext'

const QUAD_META = {
  star: { label: 'Stars', color: 'var(--success)', icon: 'S' },
  puzzle: { label: 'Hidden Gems', color: 'var(--info)', icon: 'P' },
  plowhorse: { label: 'Plowhorses', color: 'var(--warning)', icon: 'H' },
  dog: { label: 'Underperformers', color: 'var(--danger)', icon: 'U' },
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      className={active ? 'btn btn-primary' : 'btn btn-ghost'}
      onClick={onClick}
      style={{ fontSize: 12 }}
    >
      {children}
    </button>
  )
}

export default function MenuAnalysis() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const initialTab = tabParam === 'price-opportunities' ? 'price' : tabParam === 'profitability' ? 'profitability' : tabParam === 'velocity' ? 'velocity' : 'matrix'

  const [activeTab, setActiveTab] = useState(initialTab)
  const [data, setData] = useState(null)
  const [trends, setTrends] = useState(null)
  const [priceApi, setPriceApi] = useState([])
  const [combos, setCombos] = useState([])
  const [totalOrders, setTotalOrders] = useState(0)
  const [loading, setLoading] = useState(true)
  const [trendsLoading, setTrendsLoading] = useState(true)
  const [categoryBreakdown, setCategoryBreakdown] = useState([])
  const [quadrantFilter, setQuadrantFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [showAllCategoryTrends, setShowAllCategoryTrends] = useState(false)
  const [trendSortBy, setTrendSortBy] = useState('revenue_last_30d')
  const [trendSortDir, setTrendSortDir] = useState('desc')
  const [acknowledged, setAcknowledged] = useState({})

  useEffect(() => {
    let active = true
    Promise.all([
      getMenuMatrix(),
      getTrends().catch(() => null),
      getPriceRecommendations().catch(() => ({ recommendations: [] })),
      getCombos().catch(() => ({ combos: [] })),
      getDashboardMetrics().catch(() => ({ total_orders: 0 })),
      getCategoryBreakdown().catch(() => ({ categories: [] })),
    ])
      .then(([matrixData, trendsData, priceData, comboData, metrics, catData]) => {
        if (!active) return
        setData(matrixData)
        setTrends(trendsData)
        setPriceApi(priceData?.recommendations || [])
        setCombos(comboData?.combos || [])
        setTotalOrders(metrics?.total_orders || 0)
        setCategoryBreakdown(catData?.categories || [])
      })
      .catch((err) => {
        console.error('Menu Analysis load failed:', err)
      })
      .finally(() => {
        if (!active) return
        setLoading(false)
        setTrendsLoading(false)
      })

    return () => { active = false }
  }, [])

  useEffect(() => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (activeTab === 'price') next.set('tab', 'price-opportunities')
      else if (activeTab === 'profitability') next.set('tab', 'profitability')
      else if (activeTab === 'velocity') next.set('tab', 'velocity')
      else next.delete('tab')
      return next
    }, { replace: true })
  }, [activeTab, setSearchParams])

  const categoryTrends = useMemo(() => {
    const rows = [...(trends?.category_trends || [])]
      .filter((row) => {
        if (showAllCategoryTrends) return true
        return (row.revenue_last_30d || 0) > 0 || (row.revenue_prev_30d || 0) > 0
      })

    rows.sort((a, b) => {
      const aVal = a[trendSortBy] || 0
      const bVal = b[trendSortBy] || 0
      return trendSortDir === 'desc' ? bVal - aVal : aVal - bVal
    })
    return rows
  }, [trends, showAllCategoryTrends, trendSortBy, trendSortDir])

  const priceInsight = useMemo(() => buildPriceOpportunities({
    items: data?.items || [],
    combos,
    apiRecommendations: priceApi,
    totalOrders,
  }), [data, combos, priceApi, totalOrders])

  // --- Profitability tab data ---
  const marginTiers = useMemo(() => {
    const allItems = data?.items || []
    const high = allItems.filter((i) => (i.margin_pct || i.cm_percent || 0) >= 65).length
    const medium = allItems.filter((i) => { const m = i.margin_pct || i.cm_percent || 0; return m >= 50 && m < 65 }).length
    const low = allItems.filter((i) => (i.margin_pct || i.cm_percent || 0) < 50).length
    return [
      { tier: 'High (≥65%)', count: high, color: 'var(--success)' },
      { tier: 'Medium (50–65%)', count: medium, color: 'var(--warning)' },
      { tier: 'Low (<50%)', count: low, color: 'var(--danger)' },
    ]
  }, [data])

  const categoryMargins = useMemo(() => {
    const allItems = data?.items || []
    const catMap = new Map()
    for (const item of allItems) {
      const cat = item.category || 'Uncategorized'
      const entry = catMap.get(cat) || { category: cat, totalMargin: 0, totalRevenue: 0, count: 0 }
      entry.totalMargin += (item.margin_pct || item.cm_percent || 0)
      entry.totalRevenue += (item.revenue_30d || item.total_revenue || 0)
      entry.count += 1
      catMap.set(cat, entry)
    }
    return [...catMap.values()]
      .map((c) => ({ ...c, avgMargin: c.count > 0 ? c.totalMargin / c.count : 0 }))
      .sort((a, b) => b.avgMargin - a.avgMargin)
  }, [data])

  // --- Velocity tab data ---
  const popularityTiers = useMemo(() => {
    const allItems = data?.items || []
    const high = allItems.filter((i) => (i.popularity_score || 0) >= 0.6).length
    const medium = allItems.filter((i) => { const p = i.popularity_score || 0; return p >= 0.3 && p < 0.6 }).length
    const low = allItems.filter((i) => (i.popularity_score || 0) < 0.3).length
    return [
      { tier: 'High (≥0.6)', count: high, color: 'var(--success)' },
      { tier: 'Medium (0.3–0.6)', count: medium, color: 'var(--warning)' },
      { tier: 'Low (<0.3)', count: low, color: 'var(--danger)' },
    ]
  }, [data])

  if (loading) {
    return (
      <div className="app-page">
        <div className="skeleton" style={{ height: 84, marginBottom: 'var(--space-5)' }} />
        <div className="skeleton" style={{ height: 42, marginBottom: 'var(--space-5)' }} />
        <div className="skeleton" style={{ height: 360, marginBottom: 'var(--space-5)' }} />
        <div className="skeleton" style={{ height: 220 }} />
      </div>
    )
  }

  if (!data || !data.items) {
    return <div className="loading">Failed to load data. Is the backend running?</div>
  }

  const items = data.items || []
  const categories = ['all', ...Array.from(new Set(items.map((i) => i.category)))]

  const itemTrendMap = {}
  if (trends?.item_trends) {
    for (const trend of trends.item_trends) itemTrendMap[trend.item_id] = trend
  }

  const enrichedItems = items.map((item) => {
    const trend = itemTrendMap[item.item_id]
    return {
      ...item,
      revenue_trend_arrow: trend?.revenue_trend_arrow || '',
      popularity_trend_arrow: trend?.popularity_trend_arrow || '',
      revenue_trend_pct: trend?.revenue_trend_pct || 0,
      direction: trend?.direction || '',
    }
  })

  const quadrantCounts = {
    star: items.filter((i) => i.quadrant === 'star').length,
    puzzle: items.filter((i) => i.quadrant === 'puzzle').length,
    plowhorse: items.filter((i) => i.quadrant === 'plowhorse').length,
    dog: items.filter((i) => i.quadrant === 'dog').length,
  }

  const driftItems = trends?.quadrant_drift || []
  const driftByQuadrant = {}
  for (const drift of driftItems) {
    driftByQuadrant[drift.current_quadrant] = (driftByQuadrant[drift.current_quadrant] || 0) + 1
  }

  const itemsByMargin = [...enrichedItems].sort((a, b) => (b.margin_pct || b.cm_percent || 0) - (a.margin_pct || a.cm_percent || 0))

  const itemsByVelocity = [...enrichedItems].sort((a, b) => (b.popularity_score || 0) - (a.popularity_score || 0))

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

  const handleTrendSort = (column) => {
    if (trendSortBy === column) {
      setTrendSortDir((prev) => (prev === 'desc' ? 'asc' : 'desc'))
    } else {
      setTrendSortBy(column)
      setTrendSortDir('desc')
    }
  }

  const trendSortIcon = (column) => (trendSortBy === column ? (trendSortDir === 'desc' ? ' v' : ' ^') : '')

  return (
    <motion.div
      className="app-page"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div className="app-hero" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div>
          <div className="app-hero-eyebrow">{t('page_menu_eyebrow')}</div>
          <h1 className="app-hero-title">{t('page_menu_title')}</h1>
          <p className="app-hero-sub">{t('page_menu_sub')}</p>
        </div>
      </motion.div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-4)', flexWrap: 'wrap' }}>
        <TabButton active={activeTab === 'matrix'} onClick={() => setActiveTab('matrix')}>{t('page_menu_tab_matrix')}</TabButton>
        <TabButton active={activeTab === 'profitability'} onClick={() => setActiveTab('profitability')}>Profitability</TabButton>
        <TabButton active={activeTab === 'velocity'} onClick={() => setActiveTab('velocity')}>Popularity &amp; Velocity</TabButton>
        <TabButton active={activeTab === 'price'} onClick={() => setActiveTab('price')}>{t('page_menu_tab_price')}</TabButton>
      </div>

      {activeTab === 'matrix' && (
        <>
          {trendsLoading && (
            <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
              <div className="card-body" style={{ padding: 'var(--space-3) var(--space-5)' }}>
                <div className="skeleton" style={{ height: 16 }} />
              </div>
            </div>
          )}

          <div className="quadrant-chip-row">
            {Object.entries(QUAD_META).map(([id, meta]) => {
              const active = quadrantFilter === id
              return (
                <button
                  key={id}
                  className={`quadrant-chip ${active ? 'quadrant-chip--active' : ''}`}
                  style={{ '--quad-color': meta.color }}
                  onClick={() => setQuadrantFilter(active ? 'all' : id)}
                >
                  <span className="quadrant-chip-icon">{meta.icon}</span>
                  <span className="quadrant-chip-count">{quadrantCounts[id]}</span>
                  <span className="quadrant-chip-label">{meta.label}</span>
                  <span className="quadrant-chip-drift">{driftByQuadrant[id] || 0} drifting</span>
                </button>
              )
            })}
          </div>

          <div className="grid-2">
            <div className="card" style={{ marginBottom: 24 }}>
              <div className="card-header">BCG Menu Matrix</div>
              <div className="card-body">
                <MenuMatrix items={items} />
              </div>
            </div>

            <div className="card">
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Menu Items</span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}>
                    {categories.map((category) => (
                      <option key={category} value={category}>{category === 'all' ? 'All Categories' : category}</option>
                    ))}
                  </select>
                  {quadrantFilter !== 'all' && (
                    <button className="btn btn-ghost" onClick={() => setQuadrantFilter('all')} style={{ padding: '4px 8px', fontSize: 12 }}>
                      Clear
                    </button>
                  )}
                </div>
              </div>
              <div className="card-body" style={{ padding: 0, maxHeight: 460, overflowY: 'auto' }}>
                <ItemTable items={enrichedItems} categoryFilter={categoryFilter} quadrantFilter={quadrantFilter} />
              </div>
            </div>
          </div>

          {categoryTrends.length > 0 && (
            <ScrollReveal variants={fadeInUp}>
              <div className="card" style={{ marginTop: 24 }}>
                <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>Category Revenue Trends (30-day)</span>
                  <button className="btn btn-ghost" style={{ fontSize: 11 }} onClick={() => setShowAllCategoryTrends((prev) => !prev)}>
                    {showAllCategoryTrends ? 'Hide Zero-Revenue' : 'Show All'}
                  </button>
                </div>
                <div className="card-body" style={{ padding: 0 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Category</th>
                        <th style={{ textAlign: 'right', cursor: 'pointer' }} onClick={() => handleTrendSort('revenue_last_30d')}>Revenue (Last 30d){trendSortIcon('revenue_last_30d')}</th>
                        <th style={{ textAlign: 'right', cursor: 'pointer' }} onClick={() => handleTrendSort('revenue_prev_30d')}>Revenue (Prev 30d){trendSortIcon('revenue_prev_30d')}</th>
                        <th style={{ textAlign: 'right', cursor: 'pointer' }} onClick={() => handleTrendSort('trend_pct')}>Trend{trendSortIcon('trend_pct')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {categoryTrends.map((row, index) => (
                        <tr key={index}>
                          <td style={{ fontWeight: 600 }}>{row.category_name}</td>
                          <td className="col-number">₹{(row.revenue_last_30d || 0).toLocaleString('en-IN')}</td>
                          <td className="col-number">₹{(row.revenue_prev_30d || 0).toLocaleString('en-IN')}</td>
                          <td className="col-number" style={{ fontWeight: 700, color: row.trend_pct > 0 ? 'var(--success)' : row.trend_pct < 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                            {row.trend_arrow} {row.trend_pct > 0 ? '+' : ''}{row.trend_pct}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </ScrollReveal>
          )}
        </>
      )}

      {activeTab === 'profitability' && (
        <>
          <div className="grid-3" style={{ marginBottom: 'var(--space-6)' }}>
            {marginTiers.map((t) => (
              <div key={t.tier} className="card">
                <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-5)' }}>
                  <div style={{ fontSize: 32, fontWeight: 800, color: t.color }}>{t.count}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{t.tier}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card">
              <div className="card-header">Margin Distribution by Category</div>
              <div className="card-body">
                {categoryMargins.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No category data available.</div>
                ) : (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={categoryMargins} layout="vertical" margin={{ top: 10, right: 12, left: 12, bottom: 10 }}>
                      <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                      <YAxis dataKey="category" type="category" width={110} tick={{ fill: 'var(--text-primary)', fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={CHART_TOOLTIP} itemStyle={{ color: '#fff' }} labelStyle={{ color: '#fff' }} formatter={(v) => `${v.toFixed(1)}%`} cursor={{ fill: 'var(--bg-overlay)' }} />
                      <Bar dataKey="avgMargin" radius={[0, 6, 6, 0]} background={{ fill: 'rgba(255,255,255,0.05)', radius: [0, 6, 6, 0] }}>
                        {categoryMargins.map((c, i) => (
                          <Cell key={i} fill={c.avgMargin >= 65 ? 'var(--success)' : c.avgMargin >= 50 ? 'var(--warning)' : 'var(--danger)'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            <div className="card">
              <div className="card-header">Margin Tier Breakdown</div>
              <div className="card-body" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={marginTiers.filter((t) => t.count > 0)}
                      dataKey="count"
                      nameKey="tier"
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={3}
                      label={({ tier, count }) => `${tier}: ${count}`}
                    >
                      {marginTiers.filter((t) => t.count > 0).map((t, i) => (
                        <Cell key={i} fill={t.color === 'var(--success)' ? '#2A7A50' : t.color === 'var(--warning)' ? '#C07A20' : '#D94841'} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={CHART_TOOLTIP} itemStyle={{ color: '#fff' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">All Items by Contribution Margin</div>
            <div className="card-body" style={{ padding: 0, maxHeight: 480, overflowY: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Item</th>
                    <th>Category</th>
                    <th style={{ textAlign: 'right' }}>Price</th>
                    <th style={{ textAlign: 'right' }}>CM%</th>
                    <th>Tier</th>
                    <th>Quadrant</th>
                    <th>ML</th>
                  </tr>
                </thead>
                <tbody>
                  {itemsByMargin.map((item, idx) => {
                    const m = item.margin_pct || item.cm_percent || 0
                    const tier = m >= 65 ? 'High' : m >= 50 ? 'Medium' : 'Low'
                    const tierColor = m >= 65 ? 'var(--success)' : m >= 50 ? 'var(--warning)' : 'var(--danger)'
                    return (
                      <tr key={item.item_id}>
                        <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{idx + 1}</td>
                        <td style={{ fontWeight: 600 }}>{item.name}</td>
                        <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.category}</td>
                        <td className="col-number" style={{ fontWeight: 600 }}>{formatRupees(item.selling_price)}</td>
                        <td className="col-number" style={{ fontWeight: 700, color: tierColor, fontFamily: 'var(--font-mono)' }}>{m.toFixed(1)}%</td>
                        <td><span className="profitability-tier-badge" style={{ '--tier-color': tierColor }}>{tier}</span></td>
                        <td style={{ fontSize: 12, textTransform: 'capitalize' }}>{item.quadrant}</td>
                        <td>
                          {(item.ml_profitability_score != null || item.ml_profit_tier) && (
                            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                              {item.ml_profitability_score != null && <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{item.ml_profitability_score}</span>}
                              {item.ml_profit_tier && <span style={{ marginLeft: 4, background: 'color-mix(in srgb, var(--info) 15%, transparent)', padding: '1px 6px', borderRadius: 4 }}>ML {item.ml_profit_tier}</span>}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {activeTab === 'velocity' && (
        <>
          <div className="grid-3" style={{ marginBottom: 'var(--space-6)' }}>
            {popularityTiers.map((t) => (
              <div key={t.tier} className="card">
                <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-5)' }}>
                  <div style={{ fontSize: 32, fontWeight: 800, color: t.color }}>{t.count}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{t.tier}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
            <div className="card-header">Items by Popularity Score</div>
            <div className="card-body" style={{ padding: 0, maxHeight: 520, overflowY: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Item</th>
                    <th>Category</th>
                    <th style={{ textAlign: 'right' }}>Popularity</th>
                    <th>Classification</th>
                    <th>Trend</th>
                    <th style={{ textAlign: 'right' }}>CM%</th>
                    <th>Quadrant</th>
                    <th>ML</th>
                  </tr>
                </thead>
                <tbody>
                  {itemsByVelocity.map((item, idx) => {
                    const pop = item.popularity_score || 0
                    const tier = pop >= 0.6 ? 'High' : pop >= 0.3 ? 'Medium' : 'Low'
                    const tierColor = pop >= 0.6 ? 'var(--success)' : pop >= 0.3 ? 'var(--warning)' : 'var(--danger)'
                    const m = item.margin_pct || item.cm_percent || 0
                    const velLabel = item.ml_velocity_label
                    const velPct = item.ml_velocity_trend_pct
                    const mlConf = item.ml_confidence
                    return (
                      <tr key={item.item_id}>
                        <td style={{ color: 'var(--text-muted)', fontSize: 11 }}>{idx + 1}</td>
                        <td style={{ fontWeight: 600 }}>{item.name}</td>
                        <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.category}</td>
                        <td className="col-number">
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end' }}>
                            <div style={{ width: 60, height: 6, background: 'var(--bg-overlay)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                              <div style={{ width: `${Math.round(pop * 100)}%`, height: '100%', background: tierColor, borderRadius: 'var(--radius-full)' }} />
                            </div>
                            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 12 }}>{(pop * 100).toFixed(0)}</span>
                          </div>
                        </td>
                        <td><span className="profitability-tier-badge" style={{ '--tier-color': tierColor }}>{tier}</span></td>
                        <td>
                          {item.popularity_trend_arrow ? (
                            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: item.revenue_trend_pct > 0 ? 'var(--success)' : item.revenue_trend_pct < 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                              {item.popularity_trend_arrow}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>—</span>
                          )}
                        </td>
                        <td className="col-number" style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: m >= 65 ? 'var(--success)' : m >= 50 ? 'var(--warning)' : 'var(--danger)' }}>
                          {m.toFixed(1)}%
                        </td>
                        <td style={{ fontSize: 12, textTransform: 'capitalize' }}>{item.quadrant}</td>
                        <td>
                          {(velLabel != null || velPct != null || mlConf != null) && (
                            <span style={{ fontSize: 11, display: 'flex', flexDirection: 'column', gap: 2 }}>
                              {velPct != null && <span style={{ fontFamily: 'var(--font-mono)', color: velPct > 0 ? 'var(--success)' : velPct < 0 ? 'var(--danger)' : 'var(--text-muted)' }}>{velPct > 0 ? '+' : ''}{velPct}% 7d</span>}
                              {velLabel && <span style={{ background: 'color-mix(in srgb, var(--info) 15%, transparent)', padding: '1px 6px', borderRadius: 4 }}>ML {velLabel.replace('_', ' ')}</span>}
                              {mlConf != null && <span style={{ color: 'var(--text-muted)' }}>{(mlConf * 100).toFixed(0)}% conf</span>}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {activeTab === 'price' && (
        <section className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Price Opportunities</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {priceInsight.opportunities.length} suggestions
            </span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {priceInsight.insufficientData && priceInsight.opportunities.length === 0 && (
              <div style={{ padding: 12, background: 'color-mix(in srgb, var(--warning) 10%, transparent)', fontSize: 12, borderBottom: '1px solid var(--border-subtle)' }}>
                Not enough order history to generate price recommendations. Suggestions will appear as more orders are placed.
              </div>
            )}

            {priceInsight.opportunities.length === 0 ? (
              <div style={{ padding: 20, fontSize: 13, color: 'var(--text-muted)' }}>
                No pricing opportunities are available. Add order and trend data, then refresh this tab.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Item Name</th>
                    <th style={{ textAlign: 'right' }}>Current Price</th>
                    <th>Suggested Price / Action</th>
                    <th style={{ textAlign: 'right' }}>Expected CM Impact</th>
                    <th style={{ textAlign: 'right' }}>Expected Volume Impact</th>
                    <th>Confidence</th>
                    <th>ML</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {priceInsight.opportunities.map((row) => (
                    <tr key={row.id}>
                      <td style={{ fontWeight: 600 }}>{row.item_name}</td>
                      <td className="col-number">₹{Number(row.current_price || 0).toLocaleString('en-IN')}</td>
                      <td>{row.suggested_action}</td>
                      <td className="col-number" style={{ color: String(row.expected_cm_impact).includes('+') ? 'var(--success)' : 'var(--text-secondary)' }}>{row.expected_cm_impact}</td>
                      <td className="col-number" style={{ color: String(row.expected_volume_impact).includes('+') ? 'var(--success)' : 'var(--text-secondary)' }}>{row.expected_volume_impact}</td>
                      <td>{row.confidence_level}</td>
                      <td>
                        {(row.ml_opportunity_score != null || row.ml_badge) && (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, background: 'color-mix(in srgb, var(--info) 18%, transparent)', color: 'var(--info)', padding: '2px 8px', borderRadius: 'var(--radius-full)', fontWeight: 600 }}>
                            ML {row.ml_badge || (row.ml_opportunity_score != null ? `${(row.ml_opportunity_score * 100).toFixed(0)}%` : '')}
                          </span>
                        )}
                      </td>
                      <td>
                        <button
                          className={acknowledged[row.id] ? 'btn btn-secondary' : 'btn btn-ghost'}
                          style={{ fontSize: 11 }}
                          onClick={async () => {
                            if (row.suggested_price && row.item_id) {
                              try {
                                const { updateMenuItemPrice } = await import('../api/client')
                                await updateMenuItemPrice(row.item_id, row.suggested_price)
                                setAcknowledged((prev) => ({ ...prev, [row.id]: true }))
                              } catch (err) {
                                console.error('Price update failed:', err)
                              }
                            } else {
                              setAcknowledged((prev) => ({ ...prev, [row.id]: true }))
                            }
                          }}
                          disabled={!!acknowledged[row.id]}
                        >
                          {acknowledged[row.id] ? 'Applied' : 'Apply Suggestion'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      )}
    </motion.div>
  )
}

