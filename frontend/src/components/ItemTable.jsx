import { memo, useMemo, useState } from 'react'
import { useThresholds } from '../context/SettingsContext'

const QUADRANT_META = {
  star: { label: 'Star', icon: '⭐', tagClass: 'tag-star' },
  puzzle: { label: 'Puzzle', icon: '🔷', tagClass: 'tag-puzzle' },
  plowhorse: { label: 'Plowhorse', icon: '🐴', tagClass: 'tag-amber' },
  dog: { label: 'Underperformer', icon: '📉', tagClass: 'tag-red' },
}

function ItemTable({ items, categoryFilter, quadrantFilter }) {
  const [sortBy, setSortBy] = useState('margin_pct')
  const [sortDir, setSortDir] = useState('desc')
  const thresholds = useThresholds()

  if (!items || items.length === 0) {
    return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>No items to display</div>
  }

  const sorted = useMemo(() => {
    const filtered = items.filter((item) => {
      if (categoryFilter !== 'all' && item.category !== categoryFilter) return false
      if (quadrantFilter !== 'all' && item.quadrant !== quadrantFilter) return false
      return true
    })

    return [...filtered].sort((a, b) => {
      const aVal = a[sortBy] ?? 0
      const bVal = b[sortBy] ?? 0
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal
    })
  }, [items, categoryFilter, quadrantFilter, sortBy, sortDir])

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortDir((prev) => (prev === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortBy(column)
      setSortDir('desc')
    }
  }

  const sortIcon = (column) => (sortBy === column ? (sortDir === 'desc' ? ' ↓' : ' ↑') : '')

  const cmColor = (value) => {
    if (value >= thresholds.cm_green_min) return 'var(--success)'
    if (value >= thresholds.cm_yellow_min) return 'var(--warning)'
    return 'var(--danger)'
  }

  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Item</th>
          <th>Category</th>
          <th style={{ cursor: 'pointer', textAlign: 'right' }} onClick={() => handleSort('selling_price')}>
            Price{sortIcon('selling_price')}
          </th>
          <th style={{ cursor: 'pointer', textAlign: 'right' }} onClick={() => handleSort('margin_pct')}>
            CM%{sortIcon('margin_pct')}
          </th>
          <th title="Popularity score from 0 to 1. Higher means more frequently ordered.">Popularity</th>
          <th>Quadrant</th>
          <th>Trend</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((item) => {
          const qMeta = QUADRANT_META[item.quadrant] || { label: item.quadrant, icon: '', tagClass: 'tag-gray' }
          const popularityRaw = Number(item.popularity_score || 0)
          const popularityPct = Math.max(0, Math.min(100, popularityRaw <= 1 ? popularityRaw * 100 : popularityRaw))
          const marginPct = Number(item.margin_pct || item.cm_percent || 0)
          const popTier = popularityPct >= 60 ? 'High' : popularityPct >= 30 ? 'Med' : 'Low'
          const popTierColor = popularityPct >= 60 ? 'var(--success)' : popularityPct >= 30 ? 'var(--warning)' : 'var(--danger)'

          return (
            <tr key={item.item_id}>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 3, height: 28, borderRadius: 2, background: cmColor(marginPct), flexShrink: 0 }} />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{item.name}</div>
                  </div>
                </div>
              </td>
              <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.category}</td>
              <td className="col-number" style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                ₹{item.selling_price}
              </td>
              <td className="col-number">
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, color: cmColor(marginPct) }}>
                  {marginPct.toFixed(1)}%
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 60, height: 8, background: 'var(--bg-overlay)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                    <div style={{ width: `${popularityPct}%`, height: '100%', background: popTierColor, borderRadius: 'var(--radius-full)', transition: 'width 0.6s ease' }} />
                  </div>
                  <span className="profitability-tier-badge" style={{ '--tier-color': popTierColor, fontSize: 9, padding: '1px 5px' }}>{popTier}</span>
                </div>
              </td>
              <td>
                <span className={`tag ${qMeta.tagClass}`}>
                  <span style={{ marginRight: 4 }}>{qMeta.icon}</span>
                  {qMeta.label}
                </span>
              </td>
              <td>
                {item.revenue_trend_arrow ? (
                  <span
                    style={{
                      fontSize: 13,
                      fontFamily: 'var(--font-mono)',
                      color: item.revenue_trend_pct > 0 ? 'var(--success)' : item.revenue_trend_pct < 0 ? 'var(--danger)' : 'var(--text-muted)',
                      fontWeight: 600,
                    }}
                    title={`Revenue: ${item.revenue_trend_pct > 0 ? '+' : ''}${item.revenue_trend_pct}%`}
                  >
                    {item.revenue_trend_arrow}
                  </span>
                ) : (
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>-</span>
                )}
              </td>
              <td style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 220 }}>{item.action || item.action_recommendation}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export default memo(ItemTable)
