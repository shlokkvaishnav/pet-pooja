import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cancelOpsOrder, createOpsOrder, getOpsOrder, getOpsOrders, updateOpsOrder } from '../api/client'
import { formatRupees, formatRupeesShort } from '../utils/format'
import { motion } from 'motion/react'

const statusColors = {
  building: 'var(--warning)',
  confirmed: 'var(--success)',
  cancelled: 'var(--danger)',
}

function formatOrderId(order) {
  if (order.order_number) return `#${order.order_number}`
  const raw = (order.order_id || '').replace(/-/g, '').toUpperCase()
  if (!raw) return '#N/A'
  return `#${raw.slice(0, 8)}`
}

export default function Orders() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [orderType, setOrderType] = useState('')
  const [source, setSource] = useState('')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [page, setPage] = useState(1)
  const [busyOrderId, setBusyOrderId] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [orderPreview, setOrderPreview] = useState(null)
  const limit = 20

  useEffect(() => {
    const id = setTimeout(() => setDebouncedSearch(search.trim()), 300)
    return () => clearTimeout(id)
  }, [search])

  const params = useMemo(
    () => ({
      limit,
      offset: (page - 1) * limit,
      status: status || undefined,
      order_type: orderType || undefined,
      source: source || undefined,
      search: debouncedSearch || undefined,
    }),
    [page, status, orderType, source, debouncedSearch],
  )

  const refreshOrders = () => getOpsOrders(params).then(setData)

  useEffect(() => {
    setLoading(true)
    setError('')
    getOpsOrders(params)
      .then(setData)
      .catch((err) => setError(err?.detail || err?.message || 'Failed to load orders'))
      .finally(() => setLoading(false))
  }, [params])

  const handleCreateOrder = async () => {
    setBusyOrderId('create')
    setNotice('')
    setError('')
    try {
      const nextTable = window.prompt('Table number for new order (optional):', '')
      await createOpsOrder({
        source: 'manual',
        order_type: 'dine_in',
        status: 'building',
        total_amount: 0,
        table_number: (nextTable || '').trim() || null,
      })
      await refreshOrders()
      setNotice('Manual order created successfully.')
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not create order')
    } finally {
      setBusyOrderId('')
    }
  }

  const handleViewOrder = async (orderId) => {
    setBusyOrderId(orderId)
    setError('')
    try {
      const details = await getOpsOrder(orderId)
      setOrderPreview(details)
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not load order details')
    } finally {
      setBusyOrderId('')
    }
  }

  const handleEditOrder = async (order) => {
    setBusyOrderId(order.order_id)
    setNotice('')
    setError('')
    try {
      const nextTable = window.prompt('Update table number (leave blank to clear):', order.table_number || '')
      const nextAmountRaw = window.prompt('Update total amount:', String(order.total_amount || 0))
      const parsedAmount = Number(nextAmountRaw)
      if (Number.isNaN(parsedAmount) || parsedAmount < 0) {
        throw new Error('Total amount must be a non-negative number.')
      }
      await updateOpsOrder(order.order_id, {
        table_number: (nextTable || '').trim() || null,
        total_amount: parsedAmount,
      })
      await refreshOrders()
      setNotice(`Order ${formatOrderId(order)} updated.`)
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not update order')
    } finally {
      setBusyOrderId('')
    }
  }

  const handleCancelOrder = async (order) => {
    if (order.status === 'cancelled') return
    const ok = window.confirm(`Cancel order ${formatOrderId(order)}?`)
    if (!ok) return

    setBusyOrderId(order.order_id)
    setNotice('')
    setError('')
    try {
      await cancelOpsOrder(order.order_id)
      await refreshOrders()
      setNotice(`Order ${formatOrderId(order)} cancelled.`)
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not cancel order')
    } finally {
      setBusyOrderId('')
    }
  }

  if (loading) return <div className="loading">Loading orders...</div>
  if (!data) return <div className="loading">Failed to load orders.</div>

  const { summary, orders, total } = data
  const totalPages = Math.max(1, Math.ceil((total || 0) / limit))
  const hasOrders = orders.length > 0

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">Operations</div>
          <h1 className="app-hero-title">Orders</h1>
          <p className="app-hero-sub">Live order flow and status monitoring.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <button className="btn btn-primary" onClick={handleCreateOrder} disabled={busyOrderId === 'create'}>
            + New Order
          </button>
          <button className="btn btn-ghost" onClick={() => navigate('/dashboard/voice-order')}>
            Voice Order
          </button>
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
      </div>

      {(notice || error) ? (
        <div className="card">
          <div className="card-body" style={{ fontSize: 12, color: error ? 'var(--danger)' : 'var(--success)' }}>
            {error || notice}
          </div>
        </div>
      ) : null}

      {orderPreview ? (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Order Details</span>
            <button className="btn btn-ghost" onClick={() => setOrderPreview(null)}>Close</button>
          </div>
          <div className="card-body">
            <div className="app-grid-3">
              <div>
                <div className="app-card-label">Order ID</div>
                <div className="app-card-value" style={{ fontSize: 18 }}>{formatOrderId(orderPreview)}</div>
              </div>
              <div>
                <div className="app-card-label">Status</div>
                <div className="app-card-value" style={{ fontSize: 18 }}>{orderPreview.status}</div>
              </div>
              <div>
                <div className="app-card-label">Amount</div>
                <div className="app-card-value" style={{ fontSize: 18 }}>{formatRupees(orderPreview.total_amount || 0)}</div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div className="app-grid-3">
        {[
          { label: 'Open Orders', value: summary.open_orders, color: 'var(--warning)' },
          { label: 'Confirmed Orders', value: summary.confirmed_orders, color: 'var(--success)' },
          { label: 'Cancelled Orders', value: summary.cancelled_orders, color: 'var(--danger)' },
        ].map((card) => (
          <motion.div key={card.label} className="app-card order-status-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="app-card-label">{card.label}</div>
            <div className="app-card-value" style={{ color: card.color }}>{card.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">Filters</div>
        <div className="card-body">
          <div className="filters-row orders-filters-row">
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
          {!hasOrders ? (
            <div className="orders-empty-state">
              <div className="orders-empty-icon">🧾</div>
              <h3>No orders yet</h3>
              <p>Your recent orders list will appear here once the first order is created.</p>
              <button className="btn btn-primary" onClick={() => navigate('/dashboard/voice-order')}>
                Create First Order via Voice
              </button>
            </div>
          ) : (
            <>
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
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => (
                      <tr key={order.order_id}>
                        <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{formatOrderId(order)}</td>
                        <td>{order.order_type}</td>
                        <td>{order.table_number || 'N/A'}</td>
                        <td>
                          <span className="status-pill" style={{ borderColor: statusColors[order.status] || 'var(--border-subtle)', color: statusColors[order.status] || 'var(--text-secondary)' }}>
                            {order.status}
                          </span>
                        </td>
                        <td>{order.source}</td>
                        <td>{formatRupees(order.total_amount || 0)}</td>
                        <td>{order.created_at ? new Date(order.created_at).toLocaleString() : 'N/A'}</td>
                        <td>
                          <div className="orders-row-actions">
                            <button className="btn btn-ghost" onClick={() => handleViewOrder(order.order_id)} disabled={busyOrderId === order.order_id}>View</button>
                            <button className="btn btn-ghost" onClick={() => handleEditOrder(order)} disabled={busyOrderId === order.order_id}>Edit</button>
                            <button className="btn btn-ghost" onClick={() => handleCancelOrder(order)} disabled={busyOrderId === order.order_id || order.status === 'cancelled'}>Cancel</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((prev) => Math.max(1, prev - 1))}>Prev</button>
                <div className="pagination-label">Page {page} of {totalPages}</div>
                <button className="btn btn-ghost" disabled={page >= totalPages} onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}>Next</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
