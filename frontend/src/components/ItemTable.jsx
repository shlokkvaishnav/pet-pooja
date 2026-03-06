import { useState } from 'react'

const QUADRANT_META = {
  star: { label: 'Star', color: 'var(--success)', tagClass: 'tag-star' },
  hidden_star: { label: 'Hidden Gem', color: 'var(--data-5)', tagClass: 'tag-puzzle' },
  workhorse: { label: 'Plowhorse', color: 'var(--warning)', tagClass: 'tag-amber' },
  dog: { label: 'Underperformer', color: 'var(--danger)', tagClass: 'tag-gray' },
}

export default function ItemTable({ items, categoryFilter, quadrantFilter }) {
  const [sortBy, setSortBy] = useState('cm_percent')
  const [sortDir, setSortDir] = useState('desc')

  if (!items || items.length === 0) {
    return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No items to display</div>
  }

  const filtered = items.filter(item => {
    if (categoryFilter !== 'all' && item.category !== categoryFilter) return false
    if (quadrantFilter !== 'all' && item.quadrant !== quadrantFilter) return false
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortBy] ?? 0
    const bVal = b[sortBy] ?? 0
    return sortDir === 'desc' ? bVal - aVal : aVal - bVal
  })

  const handleSort = (col) => {
    if (sortBy === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(col); setSortDir('desc') }
  }

  const sortIcon = (col) => sortBy === col ? (sortDir === 'desc' ? ' ↓' : ' ↑') : ''

  const cmColor = (v) => v >= 65 ? 'var(--success)' : v >= 50 ? 'var(--warning)' : 'var(--danger)'

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Item</th>
          <th>Category</th>
          <th style={{ cursor: 'pointer', textAlign: 'right' }} onClick={() => handleSort('selling_price')}>
            Price{sortIcon('selling_price')}
          </th>
          <th style={{ cursor: 'pointer', textAlign: 'right' }} onClick={() => handleSort('cm_percent')}>
            CM%{sortIcon('cm_percent')}
          </th>
          <th style={{ cursor: 'pointer' }} onClick={() => handleSort('popularity_score')}>
            Popularity{sortIcon('popularity_score')}
          </th>
          <th>Quadrant</th>
          <th>Trend</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map(item => {
          const qMeta = QUADRANT_META[item.quadrant] || { label: item.quadrant, color: 'var(--text-muted)', tagClass: '' }
          return (
            <tr key={item.item_id}>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {/* Margin color strip */}
                  <div style={{ width: 3, height: 28, borderRadius: 2, background: cmColor(item.cm_percent), flexShrink: 0 }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{item.name}</div>
                    {item.name_hi && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.name_hi}</div>}
                  </div>
                </div>
              </td>
              <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.category}</td>
              <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                ₹{item.selling_price}
              </td>
              <td style={{ textAlign: 'right' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13, color: cmColor(item.cm_percent) }}>
                  {item.cm_percent}%
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 60, height: 4, background: 'var(--bg-overlay)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                    <div style={{ width: `${item.popularity_score || 0}%`, height: '100%', background: 'var(--data-3)', borderRadius: 'var(--radius-full)', transition: 'width 0.6s ease' }} />
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)', minWidth: 24 }}>
                    {item.popularity_score || 0}
                  </span>
                </div>
              </td>
              <td>
                <span className={`tag ${qMeta.tagClass}`}>{qMeta.label}</span>
              </td>
              <td>
                {item.revenue_trend_arrow ? (
                  <span style={{
                    fontSize: 13, fontFamily: 'var(--font-mono)',
                    color: item.revenue_trend_pct > 0 ? 'var(--success)' : item.revenue_trend_pct < 0 ? 'var(--danger)' : 'var(--text-muted)',
                    fontWeight: 600,
                  }} title={`Revenue: ${item.revenue_trend_pct > 0 ? '+' : ''}${item.revenue_trend_pct}% | Pop: ${item.popularity_trend_arrow}`}>
                    {item.revenue_trend_arrow}
                  </span>
                ) : (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>—</span>
                )}
              </td>
              <td style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 200 }}>
                {item.action_recommendation}
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
