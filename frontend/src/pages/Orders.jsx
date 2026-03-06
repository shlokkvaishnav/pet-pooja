import { useEffect, useMemo, useState } from 'react'
import { getOpsOrders } from '../api/client'
import { formatRupees, formatRupeesShort } from '../utils/format'
import { motion } from 'motion/react'

const statusColors = {
  building: 'var(--warning)',
  confirmed: 'var(--success)',
  cancelled: 'var(--danger)',
}

export default function Orders() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [orderType, setOrderType] = useState('')
  const [source, setSource] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const limit = 20

  const params = useMemo(() => ({
    limit,
    offset: (page - 1) * limit,
    status: status || undefined,
    order_type: orderType || undefined,
    source: source || undefined,
    search: search || undefined,
  }), [page, status, orderType, source, search])

  useEffect(() => {
    setLoading(true)
    getOpsOrders(params)
      .then(setData)
      .finally(() => setLoading(false))
  }, [params])

  if (loading) {
    return <div className="loading">Loading orders...</div>
  }

  if (!data) {
    return <div className="loading">Failed to load orders.</div>
  }

  const { summary, orders, total } = data
  const totalPages = Math.max(1, Math.ceil((total || 0) / limit))

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">Operations</div>
          <h1 className="app-hero-title">Orders</h1>
          <p className="app-hero-sub">Live order flow and status monitoring.</p>
        </div>
        <div className="app-hero-metrics">
          <div className="app-kpi">
            <div className="app-kpi-label">Total Orders (30d)</div>
            <div className="app-kpi-value">{summary.total_orders}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Revenue (30d)</div>
            <div className="app-kpi-value">{formatRupeesShort(summary.total_revenue)}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label">Avg Order Value</div>
            <div className="app-kpi-value">{formatRupees(summary.avg_order_value)}</div>
          </div>
        </div>
      </div>

      <div className="app-grid-3">
        {[
          { label: 'Open', value: summary.open_orders, color: 'var(--warning)' },
          { label: 'Confirmed', value: summary.confirmed_orders, color: 'var(--success)' },
          { label: 'Cancelled', value: summary.cancelled_orders, color: 'var(--danger)' },
        ].map((s) => (
          <motion.div key={s.label} className="app-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="app-card-label">{s.label} Orders</div>
            <div className="app-card-value" style={{ color: s.color }}>{s.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">Filters</div>
        <div className="card-body">
          <div className="filters-row">
            <input
              className="input"
              placeholder="Search order id or number"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            />
            <select className="input" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
              <option value="">All Statuses</option>
              <option value="building">Open</option>
              <option value="confirmed">Confirmed</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <select className="input" value={orderType} onChange={(e) => { setOrderType(e.target.value); setPage(1) }}>
              <option value="">All Types</option>
              <option value="dine_in">Dine In</option>
              <option value="takeaway">Takeaway</option>
              <option value="delivery">Delivery</option>
            </select>
            <select className="input" value={source} onChange={(e) => { setSource(e.target.value); setPage(1) }}>
              <option value="">All Sources</option>
              <option value="voice">Voice</option>
              <option value="manual">Manual</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">Recent Orders</div>
        <div className="card-body">
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Type</th>
                  <th>Table</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Total</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => (
                  <tr key={o.order_id}>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{o.order_number || o.order_id}</td>
                    <td>{o.order_type}</td>
                    <td>{o.table_number || 'N/A'}</td>
                    <td>
                      <span className="status-pill" style={{ borderColor: statusColors[o.status] || 'var(--border-subtle)', color: statusColors[o.status] || 'var(--text-secondary)' }}>
                        {o.status}
                      </span>
                    </td>
                    <td>{o.source}</td>
                    <td>{formatRupees(o.total_amount || 0)}</td>
                    <td>{o.created_at ? new Date(o.created_at).toLocaleString() : 'N/A'}</td>
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
