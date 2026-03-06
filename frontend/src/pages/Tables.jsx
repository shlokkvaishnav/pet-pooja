import { useEffect, useMemo, useState } from 'react'
import { getOpsTablesFiltered, updateTableStatus } from '../api/client'
import { motion } from 'motion/react'

const statusStyles = {
  empty: { color: 'var(--text-secondary)', bg: 'var(--bg-elevated)' },
  occupied: { color: 'var(--success)', bg: 'var(--success-subtle)' },
  reserved: { color: 'var(--warning)', bg: 'var(--warning-subtle)' },
  cleaning: { color: 'var(--info)', bg: 'var(--info-subtle)' },
}

export default function Tables() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [section, setSection] = useState('')
  const [search, setSearch] = useState('')
  const [orderInputs, setOrderInputs] = useState({})

  const params = useMemo(() => ({
    status: status || undefined,
    section: section || undefined,
    search: search || undefined,
  }), [status, section, search])

  useEffect(() => {
    setLoading(true)
    getOpsTablesFiltered(params)
      .then(setData)
      .finally(() => setLoading(false))
  }, [params])

  if (loading) return <div className="loading">Loading tables...</div>
  if (!data) return <div className="loading">Failed to load tables.</div>

  const { summary, tables } = data

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">Reservations</div>
          <h1 className="app-hero-title">Tables</h1>
          <p className="app-hero-sub">Real-time floor visibility and reservations.</p>
        </div>
        <div className="app-hero-metrics">
          <div className="app-kpi">
            <div className="app-kpi-label">Total Tables</div>
            <div className="app-kpi-value">{summary.total_tables}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Occupied</div>
            <div className="app-kpi-value">{summary.occupied}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Reserved</div>
            <div className="app-kpi-value">{summary.reserved}</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Filters</div>
        <div className="card-body">
          <div className="filters-row">
            <input
              className="input"
              placeholder="Search table number"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All Statuses</option>
              <option value="empty">Empty</option>
              <option value="occupied">Occupied</option>
              <option value="reserved">Reserved</option>
              <option value="cleaning">Cleaning</option>
            </select>
            <input
              className="input"
              placeholder="Section"
              value={section}
              onChange={(e) => setSection(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="app-grid-4">
        {tables.map((t) => {
          const style = statusStyles[t.status] || statusStyles.empty
          return (
            <motion.div key={t.table_id} className="table-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div className="table-card-header">
                <div className="table-card-title">Table {t.table_number}</div>
                <div className="status-pill" style={{ color: style.color, borderColor: style.color, background: style.bg }}>
                  {t.status}
                </div>
              </div>
              <div className="table-card-meta">
                <div>Capacity: {t.capacity}</div>
                <div>Section: {t.section}</div>
              </div>
              <div className="table-card-footer">
                Current Order: {t.current_order_id || 'N/A'}
              </div>
              <div className="table-actions">
                <button className="btn btn-ghost" onClick={() => updateTableStatus(t.table_id, { status: 'occupied', current_order_id: t.current_order_id || null }).then(() => getOpsTablesFiltered(params).then(setData))}>
                  Mark Occupied
                </button>
                <button className="btn btn-ghost" onClick={() => updateTableStatus(t.table_id, { status: 'reserved', current_order_id: t.current_order_id || null }).then(() => getOpsTablesFiltered(params).then(setData))}>
                  Reserve
                </button>
                <button className="btn btn-ghost" onClick={() => updateTableStatus(t.table_id, { status: 'empty', current_order_id: null }).then(() => getOpsTablesFiltered(params).then(setData))}>
                  Clear
                </button>
              </div>
              <div className="table-order-edit">
                <input
                  className="input"
                  placeholder="Order ID"
                  value={orderInputs[t.table_id] || ''}
                  onChange={(e) => setOrderInputs((prev) => ({ ...prev, [t.table_id]: e.target.value }))}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => updateTableStatus(t.table_id, {
                    status: t.status,
                    current_order_id: orderInputs[t.table_id] || null,
                  }).then(() => getOpsTablesFiltered(params).then(setData))}
                >
                  Update
                </button>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
