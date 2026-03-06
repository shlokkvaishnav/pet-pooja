import { useState, useEffect } from 'react'
import { getMenuMatrix, getTrends } from '../api/client'
import MenuMatrix from '../components/MenuMatrix'
import ItemTable from '../components/ItemTable'
import { motion } from 'motion/react'
import { StaggerReveal, ScrollReveal, staggerContainer, staggerItem, fadeInUp } from '../utils/animations'

const QUAD_META = {
  star: { label: 'Stars', color: 'var(--success)' },
  hidden_star: { label: 'Hidden Gems', color: 'var(--data-5)' },
  workhorse: { label: 'Plowhorses', color: 'var(--warning)' },
  dog: { label: 'Underperformers', color: 'var(--danger)' },
}

export default function MenuAnalysis() {
  const [data, setData] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [trendsLoading, setTrendsLoading] = useState(true)
  const [quadrantFilter, setQuadrantFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')

  useEffect(() => {
    let active = true

    // Render page as soon as matrix data is ready.
    getMenuMatrix()
      .then((matrixData) => {
        if (!active) return
        setData(matrixData)
      })
      .catch(err => console.error('Menu Matrix failed:', err))
      .finally(() => {
        if (active) setLoading(false)
      })

    // Load trend enrichments in the background.
    getTrends()
      .then((trendsData) => {
        if (!active) return
        setTrends(trendsData)
      })
      .catch(() => {})
      .finally(() => {
        if (active) setTrendsLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return <div className="loading"><div className="spinner" /> Analyzing menu...</div>
  }

  if (!data || !data.items) {
    return <div className="loading">Failed to load data. Is the backend running?</div>
  }

  const { items, summary } = data
  const categories = ['all', ...Array.from(new Set(items.map(i => i.category)))]

  const itemTrendMap = {}
  if (trends?.item_trends) {
    for (const t of trends.item_trends) itemTrendMap[t.item_id] = t
  }

  const enrichedItems = items.map(item => {
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
    star: items.filter(i => i.quadrant === 'star').length,
    hidden_star: items.filter(i => i.quadrant === 'hidden_star').length,
    workhorse: items.filter(i => i.quadrant === 'workhorse').length,
    dog: items.filter(i => i.quadrant === 'dog').length,
  }

  const driftItems = trends?.quadrant_drift || []
  const driftByQuadrant = {}
  for (const d of driftItems) {
    driftByQuadrant[d.current_quadrant] = (driftByQuadrant[d.current_quadrant] || 0) + 1
  }

  return (
    <motion.div
      className="app-page"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div
        className="app-hero"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div>
          <div className="app-hero-eyebrow">Intelligence</div>
          <h1 className="app-hero-title">Menu Intelligence</h1>
          <p className="app-hero-sub">BCG matrix classification with trend analysis.</p>
        </div>
      </motion.div>

      {trendsLoading && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="card-body" style={{ fontSize: 12, color: 'var(--text-muted)', padding: 'var(--space-3) var(--space-5)' }}>
            Loading trend overlays...
          </div>
        </div>
      )}

      {/* Quadrant stat pills */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', marginBottom: 'var(--space-6)' }}>
        {Object.entries(QUAD_META).map(([id, meta]) => {
          const count = summary?.[id]?.count ?? quadrantCounts[id]
          const active = quadrantFilter === id
          return (
            <motion.button
              key={id}
              onClick={() => setQuadrantFilter(active ? 'all' : id)}
              whileHover={{ y: -2 }}
              whileTap={{ scale: 0.97 }}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: 'var(--space-2) var(--space-4)',
                borderRadius: 'var(--radius-full)',
                border: `1px solid ${active ? meta.color : 'var(--border-subtle)'}`,
                background: active ? `color-mix(in srgb, ${meta.color} 10%, transparent)` : 'var(--bg-surface)',
                cursor: 'pointer',
                color: active ? meta.color : 'var(--text-secondary)',
                fontSize: 13, fontFamily: 'var(--font-body)', fontWeight: 500,
                transition: 'var(--transition-fast)',
              }}
            >
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 16, color: meta.color }}>{count}</span>
              <span>{meta.label}</span>
              {driftByQuadrant[id] > 0 && (
                <span style={{
                  fontSize: 10, padding: '1px 5px', borderRadius: 'var(--radius-full)',
                  background: 'var(--warning-subtle)', color: 'var(--warning)',
                }}>
                  {driftByQuadrant[id]} drifting
                </span>
              )}
            </motion.button>
          )
        })}
      </div>

      <StaggerReveal className="grid-2" variants={staggerContainer}>
        {/* BCG Matrix Chart */}
        <motion.div className="card" style={{ marginBottom: 24 }} variants={staggerItem}>
          <div className="card-header">BCG Menu Matrix</div>
          <div className="card-body">
            <MenuMatrix items={items} />
          </div>
        </motion.div>

        {/* Menu Items table */}
        <motion.div className="card" variants={staggerItem}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Menu Items</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={categoryFilter}
                onChange={e => setCategoryFilter(e.target.value)}
              >
                {categories.map(c => (
                  <option key={c} value={c}>{c === 'all' ? 'All Categories' : c}</option>
                ))}
              </select>
              {quadrantFilter !== 'all' && (
                <button className="btn btn-ghost" onClick={() => setQuadrantFilter('all')} style={{ padding: '4px 8px', fontSize: 12 }}>
                  Clear
                </button>
              )}
            </div>
          </div>
          <div className="card-body" style={{ padding: 0, maxHeight: 440, overflowY: 'auto' }}>
            <ItemTable items={enrichedItems} categoryFilter={categoryFilter} quadrantFilter={quadrantFilter} />
          </div>
        </motion.div>
      </StaggerReveal>

      {/* Category Trends */}
      {trends?.category_trends?.length > 0 && (
        <ScrollReveal variants={fadeInUp}>
          <div className="card" style={{ marginTop: 24 }}>
            <div className="card-header">Category Revenue Trends (30-day)</div>
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th style={{ textAlign: 'right' }}>Revenue (Last 30d)</th>
                    <th style={{ textAlign: 'right' }}>Revenue (Prev 30d)</th>
                    <th style={{ textAlign: 'right' }}>Trend</th>
                  </tr>
                </thead>
                <tbody>
                  {trends.category_trends.map((ct, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{ct.category_name}</td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>₹{ct.revenue_last_30d?.toLocaleString('en-IN')}</td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>₹{ct.revenue_prev_30d?.toLocaleString('en-IN')}</td>
                      <td style={{
                        textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600,
                        color: ct.trend_pct > 0 ? 'var(--success)' : ct.trend_pct < 0 ? 'var(--danger)' : 'var(--text-muted)'
                      }}>
                        {ct.trend_arrow} {ct.trend_pct > 0 ? '+' : ''}{ct.trend_pct}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </ScrollReveal>
      )}
    </motion.div>
  )
}
