import { useEffect, useMemo, useState } from 'react'
import { adjustInventory, getOpsInventoryFiltered, updateIngredient } from '../api/client'
import { formatRupees } from '../utils/format'
import { motion, AnimatePresence } from 'motion/react'
import { INVENTORY_PAGE_LIMIT } from '../config'

function formatDelta(current, previous) {
  const delta = (current || 0) - (previous || 0)
  const prefix = delta >= 0 ? '+' : '-'
  return `${prefix}${formatRupees(Math.abs(delta))}`
}

function StockBar({ current, reorder }) {
  const ratio = reorder > 0 ? Math.min(current / reorder, 2) : 1
  const pct = Math.min(ratio * 50, 100)
  const color = ratio <= 1 ? 'var(--danger)' : ratio <= 1.5 ? 'var(--warning)' : 'var(--success)'
  return (
    <div style={{ width: '100%', height: 4, borderRadius: 2, background: 'var(--bg-overlay)' }}>
      <div style={{ width: `${pct}%`, height: '100%', borderRadius: 2, background: color, transition: 'width 0.4s' }} />
    </div>
  )
}

export default function Inventory() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [lowOnly, setLowOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [updates, setUpdates] = useState({})
  const [openCategory, setOpenCategory] = useState(null)
  const [showMovementModal, setShowMovementModal] = useState(false)
  const [movementLoading, setMovementLoading] = useState(false)
  const [error, setError] = useState('')
  const [movement, setMovement] = useState({
    ingredient_id: '',
    change_qty: '',
    reason: 'purchase',
    note: '',
  })
  const limit = INVENTORY_PAGE_LIMIT

  const params = useMemo(
    () => ({
      days: 30,
      limit,
      offset: (page - 1) * limit,
      search: search || undefined,
      low_stock_only: lowOnly || undefined,
    }),
    [page, search, lowOnly],
  )

  const refreshInventory = () => getOpsInventoryFiltered(params).then(setData)

  useEffect(() => {
    setLoading(true)
    setError('')
    getOpsInventoryFiltered(params)
      .then(setData)
      .catch((err) => setError(err?.detail || err?.message || 'Failed to load inventory'))
      .finally(() => setLoading(false))
  }, [params])

  const handleApplyMovement = async () => {
    if (!movement.ingredient_id || movement.change_qty === '') return
    setMovementLoading(true)
    setError('')
    try {
      await adjustInventory({
        ingredient_id: Number(movement.ingredient_id),
        change_qty: Number(movement.change_qty),
        reason: movement.reason,
        note: movement.note || null,
      })
      setMovement({ ingredient_id: '', change_qty: '', reason: 'purchase', note: '' })
      setShowMovementModal(false)
      await refreshInventory()
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not log stock movement')
    } finally {
      setMovementLoading(false)
    }
  }

  if (loading) return <div className="loading">Loading inventory...</div>
  if (!data) return <div className="loading">Failed to load inventory.</div>

  const { summary, ingredients, total } = data
  const totalPages = Math.max(1, Math.ceil((total || summary.total_ingredients || 0) / limit))
  const prevEstimate = summary.stock_value_prev_estimate || 0
  const stockTrendPositive = (summary.total_stock_value || 0) >= prevEstimate

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">Operations</div>
          <h1 className="app-hero-title">Inventory</h1>
          <p className="app-hero-sub">Stock health, reorder signals, and movement.</p>
        </div>
        <div className="app-hero-metrics">
          <div className="app-kpi">
            <div className="app-kpi-label">Stock Value</div>
            <div className="app-kpi-value">{formatRupees(summary.total_stock_value)}</div>
            <div className="inventory-kpi-context" style={{ color: stockTrendPositive ? 'var(--success)' : 'var(--danger)' }}>
              {formatDelta(summary.total_stock_value, prevEstimate)} vs {formatRupees(prevEstimate)} last month
            </div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Low Stock</div>
            <div className="app-kpi-value">{summary.low_stock_count}</div>
          </div>
        </div>
      </div>

      {error ? (
        <div className="card">
          <div className="card-body" style={{ fontSize: 12, color: 'var(--danger)' }}>{error}</div>
        </div>
      ) : null}

      <div className="card">
        <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Filters</span>
          <button className="btn btn-primary" onClick={() => setShowMovementModal(true)}>
            + Log Stock Movement
          </button>
        </div>
        <div className="card-body">
          <div className="filters-row inventory-filters-row">
            <input
              className="input"
              placeholder="Search ingredient"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            />
            <label className="checkbox-row">
              <input type="checkbox" checked={lowOnly} onChange={(e) => { setLowOnly(e.target.checked); setPage(1) }} />
              Low stock only
            </label>
          </div>
        </div>
      </div>

      {(() => {
        const grouped = {}
        ingredients.forEach((i) => {
          const cat = i.category || 'Other'
          if (!grouped[cat]) grouped[cat] = []
          grouped[cat].push(i)
        })
        const sortedGroups = Object.keys(grouped).sort((a, b) => a === 'Other' ? 1 : b === 'Other' ? -1 : a.localeCompare(b))

        return (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
            {sortedGroups.map((cat) => {
              const items = grouped[cat]
              const hasLow = items.some((i) => i.current_stock <= i.reorder_level)
              const isOpen = openCategory === cat

              return (
                <div
                  key={cat}
                  style={{
                    flex: isOpen ? '1 1 100%' : '0 0 auto',
                    order: isOpen ? -1 : 0,
                    transition: 'flex 0.3s',
                  }}
                >
                  <div
                    onClick={() => setOpenCategory(isOpen ? null : cat)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '10px 18px',
                      borderRadius: 'var(--radius-lg)',
                      border: `1.5px solid ${hasLow ? 'var(--danger)' : 'var(--success)'}`,
                      background: hasLow ? 'rgba(217,72,65,0.07)' : 'rgba(42,122,80,0.07)',
                      cursor: 'pointer',
                      userSelect: 'none',
                      transition: 'background 0.2s, border-color 0.2s',
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: hasLow ? 'var(--danger)' : 'var(--success)',
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>{cat}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>({items.length})</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>▼</span>
                  </div>

                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25 }}
                        style={{ overflow: 'hidden', marginTop: 'var(--space-3)' }}
                      >
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 'var(--space-3)' }}>
                          {items.map((i) => {
                            const isLow = i.current_stock <= i.reorder_level
                            return (
                              <div
                                key={i.ingredient_id}
                                style={{
                                  border: `1px solid ${isLow ? 'var(--danger)' : 'var(--border-subtle)'}`,
                                  borderRadius: 'var(--radius-lg)',
                                  padding: 'var(--space-4)',
                                  background: isLow ? 'rgba(140,42,42,0.06)' : 'var(--bg-surface)',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: 8,
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <span style={{ fontWeight: 700, fontSize: 13 }}>{i.name}</span>
                                  {isLow && <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--danger)', textTransform: 'uppercase' }}>Low</span>}
                                </div>
                                <StockBar current={i.current_stock} reorder={i.reorder_level} />
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-secondary)' }}>
                                  <span>{i.current_stock} {i.unit}</span>
                                  <span>Reorder: {i.reorder_level}</span>
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                                  Cost: {formatRupees(i.cost_per_unit)}/{i.unit}
                                </div>
                                <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                                  <input
                                    className="input input-sm"
                                    type="number"
                                    step="0.01"
                                    placeholder="Reorder"
                                    style={{ flex: 1, fontSize: 11 }}
                                    value={updates[i.ingredient_id]?.reorder_level ?? ''}
                                    onChange={(e) => setUpdates((prev) => ({
                                      ...prev,
                                      [i.ingredient_id]: { ...prev[i.ingredient_id], reorder_level: e.target.value },
                                    }))}
                                  />
                                  <input
                                    className="input input-sm"
                                    type="number"
                                    step="0.01"
                                    placeholder="Cost"
                                    style={{ flex: 1, fontSize: 11 }}
                                    value={updates[i.ingredient_id]?.cost_per_unit ?? ''}
                                    onChange={(e) => setUpdates((prev) => ({
                                      ...prev,
                                      [i.ingredient_id]: { ...prev[i.ingredient_id], cost_per_unit: e.target.value },
                                    }))}
                                  />
                                  <button
                                    className="btn btn-ghost"
                                    style={{ fontSize: 11, padding: '4px 8px' }}
                                    onClick={() => updateIngredient(i.ingredient_id, {
                                      reorder_level: updates[i.ingredient_id]?.reorder_level !== undefined ? Number(updates[i.ingredient_id].reorder_level) : undefined,
                                      cost_per_unit: updates[i.ingredient_id]?.cost_per_unit !== undefined ? Number(updates[i.ingredient_id].cost_per_unit) : undefined,
                                    }).then(() => getOpsInventoryFiltered(params).then(setData))}
                                  >
                                    Save
                                  </button>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              )
            })}
          </div>
        )
      })()}

      <div className="pagination">
        <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</button>
        <div className="pagination-label">Page {page} of {totalPages}</div>
        <button className="btn btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>Next</button>
      </div>

      {showMovementModal ? (
        <div className="inventory-modal-backdrop" onClick={() => setShowMovementModal(false)}>
          <div className="inventory-modal" onClick={(e) => e.stopPropagation()}>
            <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Log Stock Movement</span>
              <button className="btn btn-ghost" onClick={() => setShowMovementModal(false)}>Close</button>
            </div>
            <div className="card-body inventory-modal-body">
              <select
                className="input"
                value={movement.ingredient_id}
                onChange={(e) => setMovement((prev) => ({ ...prev, ingredient_id: Number(e.target.value) }))}
              >
                <option value="">Select ingredient</option>
                {ingredients.map((i) => (
                  <option key={i.ingredient_id} value={i.ingredient_id}>{i.name}</option>
                ))}
              </select>
              <input
                className="input"
                type="number"
                step="0.01"
                placeholder="Quantity (+/-)"
                value={movement.change_qty}
                onChange={(e) => setMovement((prev) => ({ ...prev, change_qty: e.target.value }))}
              />
              <select
                className="input"
                value={movement.reason}
                onChange={(e) => setMovement((prev) => ({ ...prev, reason: e.target.value }))}
              >
                <option value="purchase">Purchase</option>
                <option value="usage">Usage</option>
                <option value="waste">Waste</option>
                <option value="adjustment">Adjustment</option>
              </select>
              <input
                className="input"
                placeholder="Note"
                value={movement.note}
                onChange={(e) => setMovement((prev) => ({ ...prev, note: e.target.value }))}
              />
              <button className="btn btn-primary" onClick={handleApplyMovement} disabled={movementLoading}>
                {movementLoading ? 'Applying...' : 'Apply Movement'}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
