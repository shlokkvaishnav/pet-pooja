import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getCombos, getDashboardMetrics, getMenuMatrix, getPriceRecommendations, getTrends } from '../api/client'
import MenuMatrix from '../components/MenuMatrix'
import ItemTable from '../components/ItemTable'
import { motion } from 'motion/react'
import { ScrollReveal, fadeInUp } from '../utils/animations'
import { buildPriceOpportunities } from '../utils/revenueInsights'

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
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = searchParams.get('tab') === 'price-opportunities' ? 'price' : 'matrix'

  const [activeTab, setActiveTab] = useState(initialTab)
  const [data, setData] = useState(null)
  const [trends, setTrends] = useState(null)
  const [priceApi, setPriceApi] = useState([])
  const [combos, setCombos] = useState([])
  const [totalOrders, setTotalOrders] = useState(0)
  const [loading, setLoading] = useState(true)
  const [trendsLoading, setTrendsLoading] = useState(true)
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
    ])
      .then(([matrixData, trendsData, priceData, comboData, metrics]) => {
        if (!active) return
        setData(matrixData)
        setTrends(trendsData)
        setPriceApi(priceData?.recommendations || [])
        setCombos(comboData?.combos || [])
        setTotalOrders(metrics?.total_orders || 0)
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
          <div className="app-hero-eyebrow">Intelligence</div>
          <h1 className="app-hero-title">Menu Intelligence</h1>
          <p className="app-hero-sub">Menu performance by profitability and popularity with pricing opportunities.</p>
        </div>
      </motion.div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-4)' }}>
        <TabButton active={activeTab === 'matrix'} onClick={() => setActiveTab('matrix')}>BCG Matrix</TabButton>
        <TabButton active={activeTab === 'price'} onClick={() => setActiveTab('price')}>Price Opportunities</TabButton>
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
                    {showAllCategoryTrends ? 'Hide Zero-Revenue Categories' : 'Show All'}
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
                          <td className="col-number">INR {(row.revenue_last_30d || 0).toLocaleString('en-IN')}</td>
                          <td className="col-number">INR {(row.revenue_prev_30d || 0).toLocaleString('en-IN')}</td>
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

      {activeTab === 'price' && (
        <section className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Price Opportunities</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {priceInsight.opportunities.length} suggestions
            </span>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            {priceInsight.usedSynthetic && (
              <div style={{ padding: 12, background: 'color-mix(in srgb, var(--warning) 10%, transparent)', fontSize: 12, borderBottom: '1px solid var(--border-subtle)' }}>
                Fewer than 30 orders detected. Showing synthetic pricing suggestions for analysis only.
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
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {priceInsight.opportunities.map((row) => (
                    <tr key={row.id}>
                      <td style={{ fontWeight: 600 }}>{row.item_name}</td>
                      <td className="col-number">Rs {Number(row.current_price || 0).toLocaleString('en-IN')}</td>
                      <td>{row.suggested_action}</td>
                      <td className="col-number" style={{ color: String(row.expected_cm_impact).includes('+') ? 'var(--success)' : 'var(--text-secondary)' }}>{row.expected_cm_impact}</td>
                      <td className="col-number" style={{ color: String(row.expected_volume_impact).includes('+') ? 'var(--success)' : 'var(--text-secondary)' }}>{row.expected_volume_impact}</td>
                      <td>{row.confidence_level}</td>
                      <td>
                        <button
                          className={acknowledged[row.id] ? 'btn btn-secondary' : 'btn btn-ghost'}
                          style={{ fontSize: 11 }}
                          onClick={() => {
                            setAcknowledged((prev) => ({ ...prev, [row.id]: true }))
                            console.log('Price suggestion acknowledged', row)
                          }}
                          disabled={!!acknowledged[row.id]}
                        >
                          {acknowledged[row.id] ? 'Acknowledged' : 'Apply Suggestion'}
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

