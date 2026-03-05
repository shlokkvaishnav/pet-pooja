import { useState, useEffect } from 'react'
import { getMenuMatrix, getTrends } from '../api/client'
import MenuMatrix from '../components/MenuMatrix'
import ItemTable from '../components/ItemTable'

export default function MenuAnalysis() {
  const [data, setData] = useState(null)
  const [trends, setTrends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [quadrantFilter, setQuadrantFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')

  useEffect(() => {
    Promise.all([
      getMenuMatrix(),
      getTrends().catch(() => null),
    ])
      .then(([matrixData, trendsData]) => {
        setData(matrixData)
        setTrends(trendsData)
      })
      .catch(err => console.error('Menu Matrix failed:', err))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="loading"><div className="spinner" /> Analyzing menu...</div>
  }

  if (!data || !data.items) {
    return <div className="loading">Failed to load data. Is the backend running?</div>
  }

  const { items, summary } = data
  const categories = ['all', ...Array.from(new Set(items.map(i => i.category)))]

  // Build trend lookup for items
  const itemTrendMap = {}
  if (trends?.item_trends) {
    for (const t of trends.item_trends) {
      itemTrendMap[t.item_id] = t
    }
  }

  // Enrich items with trend data
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

  // Calculate counts if backend summary isn't fully providing them yet for the new quadrants
  const quadrantCounts = {
    star: items.filter(i => i.quadrant === 'star').length,
    hidden_star: items.filter(i => i.quadrant === 'hidden_star').length,
    workhorse: items.filter(i => i.quadrant === 'workhorse').length,
    dog: items.filter(i => i.quadrant === 'dog').length,
  }

  // Drift counts per quadrant
  const driftItems = trends?.quadrant_drift || []
  const driftByQuadrant = {}
  for (const d of driftItems) {
    const q = d.current_quadrant
    driftByQuadrant[q] = (driftByQuadrant[q] || 0) + 1
  }

  return (
    <div>
      <div className="page-header">
        <h1>Menu Analysis</h1>
        <p>BCG matrix classification — Stars, Hidden Stars, Workhorses, Dogs</p>
      </div>

      {/* Quadrant Summary & Legend */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        {[
          { id: 'star', label: 'Stars', emoji: '⭐', color: 'var(--green)' },
          { id: 'hidden_star', label: 'Hidden Stars', emoji: '🔮', color: 'var(--purple)' },
          { id: 'workhorse', label: 'Workhorses', emoji: '🐴', color: 'var(--amber)' },
          { id: 'dog', label: 'Dogs', emoji: '🐕', color: 'var(--gray)' }
        ].map(q => (
          <div
            key={q.id}
            className="card"
            style={{
              cursor: 'pointer',
              borderColor: quadrantFilter === q.id ? q.color : undefined,
              boxShadow: quadrantFilter === q.id ? `0 0 0 2px ${q.color}33` : undefined
            }}
            onClick={() => setQuadrantFilter(quadrantFilter === q.id ? 'all' : q.id)}
          >
            <div className="card-body" style={{ textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 28, marginBottom: 4 }}>
                {q.emoji}
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color: q.color }}>
                {summary && summary[q.id] ? summary[q.id].count : quadrantCounts[q.id]}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {q.label}
              </div>
              {driftByQuadrant[q.id] > 0 && (
                <div style={{ fontSize: 10, color: 'var(--amber)', marginTop: 4 }}>
                  ⚡ {driftByQuadrant[q.id]} drifting
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        {/* BCG Matrix Chart (Left side) */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">BCG Menu Matrix</div>
          <div className="card-body">
            <MenuMatrix items={items} />
          </div>
        </div>

        {/* Right side panel - Filterable/Sortable table */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Menu Items</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <select
                value={categoryFilter}
                onChange={e => setCategoryFilter(e.target.value)}
                style={{
                  background: 'var(--surface2)', border: '1px solid var(--border)',
                  color: 'var(--text)', borderRadius: 4, padding: '4px 8px', fontSize: 13
                }}
              >
                {categories.map(c => (
                  <option key={c} value={c}>{c === 'all' ? 'All Categories' : c}</option>
                ))}
              </select>

              {quadrantFilter !== 'all' && (
                <button className="btn btn-secondary" onClick={() => setQuadrantFilter('all')} style={{ padding: '4px 8px', fontSize: 13 }}>
                  Clear Filter
                </button>
              )}
            </div>
          </div>
          <div className="card-body" style={{ padding: 0, maxHeight: 440, overflowY: 'auto' }}>
            <ItemTable items={enrichedItems} categoryFilter={categoryFilter} quadrantFilter={quadrantFilter} />
          </div>
        </div>
      </div>

      {/* Category Trends */}
      {trends?.category_trends?.length > 0 && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-header">📊 Category Revenue Trends (30-day comparison)</div>
          <div className="card-body" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Revenue (Last 30d)</th>
                  <th>Revenue (Prev 30d)</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                {trends.category_trends.map((ct, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{ct.category_name}</td>
                    <td>₹{ct.revenue_last_30d?.toLocaleString()}</td>
                    <td>₹{ct.revenue_prev_30d?.toLocaleString()}</td>
                    <td style={{
                      fontWeight: 600,
                      color: ct.trend_pct > 0 ? 'var(--green)' : ct.trend_pct < 0 ? 'var(--red)' : 'var(--text-muted)'
                    }}>
                      {ct.trend_arrow} {ct.trend_pct > 0 ? '+' : ''}{ct.trend_pct}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
