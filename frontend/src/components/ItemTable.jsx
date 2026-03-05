import { useState } from 'react'

export default function ItemTable({ items, categoryFilter, quadrantFilter }) {
  const [sortBy, setSortBy] = useState('cm_percent') // changed margin_pct to cm_percent
  const [sortDir, setSortDir] = useState('desc')

  if (!items || items.length === 0) {
    return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No items to display</div>
  }

  // Filter items
  const filtered = items.filter(item => {
    if (categoryFilter !== 'all' && item.category !== categoryFilter) return false
    if (quadrantFilter !== 'all' && item.quadrant !== quadrantFilter) return false
    return true
  })

  // Sort items
  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortBy] ?? 0
    const bVal = b[sortBy] ?? 0
    return sortDir === 'desc' ? bVal - aVal : aVal - bVal
  })

  const handleSort = (col) => {
    if (sortBy === col) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(col)
      setSortDir('desc')
    }
  }

  const quadrantTag = (q) => {
    const emojis = { star: '⭐', 'hidden_star': '🔮', workhorse: '🐴', dog: '🐕' }
    const tagClass = q === 'star' ? 'star' : q === 'hidden_star' ? 'puzzle' : q === 'workhorse' ? 'amber' : 'gray'
    return <span className={`tag tag-${tagClass}`}>{emojis[q]} {q?.replace('_', ' ')}</span>
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Item</th>
          <th>Category</th>
          <th style={{ cursor: 'pointer' }} onClick={() => handleSort('selling_price')}>
            Price {sortBy === 'selling_price' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
          </th>
          <th style={{ cursor: 'pointer' }} onClick={() => handleSort('cm_percent')}>
            CM % {sortBy === 'cm_percent' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
          </th>
          <th style={{ cursor: 'pointer' }} onClick={() => handleSort('popularity_score')}>
            Popularity {sortBy === 'popularity_score' ? (sortDir === 'desc' ? '↓' : '↑') : ''}
          </th>
          <th>Quadrant</th>
          <th>Trend</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map(item => (
          <tr key={item.item_id}>
            <td>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{item.name}</div>
              {item.name_hi && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.name_hi}</div>}
            </td>
            <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.category}</td>
            <td style={{ fontWeight: 600 }}>₹{item.selling_price}</td>
            <td>
              <span style={{ color: item.cm_percent >= 65 ? 'var(--green)' : item.cm_percent >= 50 ? 'var(--amber)' : 'var(--red)' }}>
                {item.cm_percent}%
              </span>
            </td>
            <td>
              <div style={{ width: 60, height: 6, background: 'var(--surface2)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${(item.popularity_score || 0)}%`, height: '100%', background: 'var(--blue)', borderRadius: 3 }} />
              </div>
            </td>
            <td>{quadrantTag(item.quadrant)}</td>
            <td>
              {item.revenue_trend_arrow ? (
                <span style={{
                  fontSize: 13,
                  color: item.revenue_trend_pct > 0 ? 'var(--green)' : item.revenue_trend_pct < 0 ? 'var(--red)' : 'var(--text-muted)',
                  fontWeight: 600,
                }} title={`Revenue: ${item.revenue_trend_pct > 0 ? '+' : ''}${item.revenue_trend_pct}% | Pop: ${item.popularity_trend_arrow}`}>
                  {item.revenue_trend_arrow}
                </span>
              ) : (
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>—</span>
              )}
            </td>
            <td style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 200 }}>
              <div style={{ fontWeight: 600 }}>{item.action_recommendation}</div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
