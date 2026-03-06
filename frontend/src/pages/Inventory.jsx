import { useEffect, useMemo, useState } from 'react'
import { adjustInventory, getOpsInventoryFiltered, updateIngredient } from '../api/client'
import { formatRupees } from '../utils/format'
import { motion } from 'motion/react'
import { INVENTORY_PAGE_LIMIT } from '../config'

function formatDelta(current, previous) {
  const delta = (current || 0) - (previous || 0)
  const prefix = delta >= 0 ? '+' : '-'
  return `${prefix}${formatRupees(Math.abs(delta))}`
}

export default function Inventory() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [lowOnly, setLowOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [updates, setUpdates] = useState({})
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

  const { summary, low_stock, ingredients, total } = data
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
        <div className="card-header">Low Stock Alerts</div>
        <div className="card-body">
          {low_stock.length === 0 ? (
            <div className="inventory-success-empty">
              <span className="inventory-success-icon">✓</span>
              <div>
                <div className="inventory-success-title">All ingredients well-stocked</div>
                <div className="inventory-success-sub">No low-stock alerts right now.</div>
              </div>
            </div>
          ) : (
            <div className="alert-list">
              {low_stock.map((i) => (
                <div key={i.ingredient_id} className="alert-row">
                  <div>
                    <div className="alert-title">{i.name}</div>
                    <div className="alert-sub">Reorder at {i.reorder_level} {i.unit}</div>
                  </div>
                  <div className="alert-value">{i.current_stock} {i.unit}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

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

      <div className="card">
        <div className="card-header">All Ingredients</div>
        <div className="card-body">
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Ingredient</th>
                  <th>Unit</th>
                  <th>Current</th>
                  <th>Reorder</th>
                  <th>Cost / Unit</th>
                  <th>Update</th>
                </tr>
              </thead>
              <tbody>
                {ingredients.map((i) => (
                  <tr key={i.ingredient_id}>
                    <td style={{ fontWeight: 600 }}>{i.name}</td>
                    <td>{i.unit}</td>
                    <td>{i.current_stock}</td>
                    <td>
                      <input
                        className="input input-sm"
                        type="number"
                        step="0.01"
                        value={updates[i.ingredient_id]?.reorder_level ?? i.reorder_level}
                        onChange={(e) => setUpdates((prev) => ({
                          ...prev,
                          [i.ingredient_id]: {
                            ...prev[i.ingredient_id],
                            reorder_level: e.target.value,
                          },
                        }))}
                      />
                    </td>
                    <td>
                      <input
                        className="input input-sm"
                        type="number"
                        step="0.01"
                        value={updates[i.ingredient_id]?.cost_per_unit ?? i.cost_per_unit}
                        onChange={(e) => setUpdates((prev) => ({
                          ...prev,
                          [i.ingredient_id]: {
                            ...prev[i.ingredient_id],
                            cost_per_unit: e.target.value,
                          },
                        }))}
                      />
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost"
                        onClick={() => updateIngredient(i.ingredient_id, {
                          reorder_level: updates[i.ingredient_id]?.reorder_level !== undefined ? Number(updates[i.ingredient_id].reorder_level) : undefined,
                          cost_per_unit: updates[i.ingredient_id]?.cost_per_unit !== undefined ? Number(updates[i.ingredient_id].cost_per_unit) : undefined,
                        }).then(() => getOpsInventoryFiltered(params).then(setData))}
                      >
                        Save
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</button>
            <div className="pagination-label">Page {page} of {totalPages}</div>
            <button className="btn btn-ghost" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>Next</button>
          </div>
        </div>
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
