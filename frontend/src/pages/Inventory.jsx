import { useEffect, useMemo, useState } from 'react'
import { adjustInventory, getOpsInventoryFiltered, updateIngredient } from '../api/client'
import { formatRupees } from '../utils/format'
import { motion } from 'motion/react'

export default function Inventory() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [lowOnly, setLowOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [adjust, setAdjust] = useState({ ingredient_id: '', change_qty: '', reason: 'purchase', note: '' })
  const [updates, setUpdates] = useState({})
  const limit = 25

  const params = useMemo(() => ({
    days: 30,
    limit,
    offset: (page - 1) * limit,
    search: search || undefined,
    low_stock_only: lowOnly || undefined,
  }), [page, search, lowOnly])

  useEffect(() => {
    setLoading(true)
    getOpsInventoryFiltered(params)
      .then(setData)
      .finally(() => setLoading(false))
  }, [params])

  if (loading) return <div className="loading">Loading inventory...</div>
  if (!data) return <div className="loading">Failed to load inventory.</div>

  const { summary, low_stock, ingredients, total } = data
  const totalPages = Math.max(1, Math.ceil((total || summary.total_ingredients || 0) / limit))

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
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Low Stock</div>
            <div className="app-kpi-value">{summary.low_stock_count}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Waste (30d)</div>
            <div className="app-kpi-value">{summary.waste_qty}</div>
          </div>
        </div>
      </div>

      <div className="app-grid-2">
        <div className="card">
          <div className="card-header">Low Stock Alerts</div>
          <div className="card-body">
            {low_stock.length === 0 ? (
              <div className="muted">No low-stock ingredients.</div>
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

        <motion.div className="app-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <div className="app-card-label">Usage vs Waste (30d)</div>
          <div className="app-card-value">{summary.usage_qty} / {summary.waste_qty}</div>
          <div className="app-card-sub">Usage / Waste quantity</div>
        </motion.div>
      </div>

      <div className="card">
        <div className="card-header">Filters & Quick Adjust</div>
        <div className="card-body">
          <div className="filters-row">
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

          <div className="adjust-row">
            <select
              className="input"
              value={adjust.ingredient_id}
              onChange={(e) => setAdjust((prev) => ({ ...prev, ingredient_id: Number(e.target.value) }))}
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
              placeholder="Qty (+/-)"
              value={adjust.change_qty}
              onChange={(e) => setAdjust((prev) => ({ ...prev, change_qty: e.target.value }))}
            />
            <select
              className="input"
              value={adjust.reason}
              onChange={(e) => setAdjust((prev) => ({ ...prev, reason: e.target.value }))}
            >
              <option value="purchase">Purchase</option>
              <option value="usage">Usage</option>
              <option value="waste">Waste</option>
              <option value="adjustment">Adjustment</option>
            </select>
            <input
              className="input"
              placeholder="Note"
              value={adjust.note}
              onChange={(e) => setAdjust((prev) => ({ ...prev, note: e.target.value }))}
            />
            <button
              className="btn btn-primary"
              onClick={() => {
                if (!adjust.ingredient_id || adjust.change_qty === '') return
                adjustInventory({
                  ingredient_id: Number(adjust.ingredient_id),
                  change_qty: Number(adjust.change_qty),
                  reason: adjust.reason,
                  note: adjust.note || null,
                }).then(() => {
                  setAdjust({ ingredient_id: '', change_qty: '', reason: 'purchase', note: '' })
                  return getOpsInventoryFiltered(params).then(setData)
                })
              }}
            >
              Apply
            </button>
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
            <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</button>
            <div className="pagination-label">Page {page} of {totalPages}</div>
            <button className="btn btn-ghost" disabled={page >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}>Next</button>
          </div>
        </div>
      </div>
    </div>
  )
}
