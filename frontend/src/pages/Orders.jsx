import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cancelOpsOrder, getOpsOrder, getOpsOrders, updateOpsOrder } from '../api/client'
import { formatRupees, formatRupeesShort } from '../utils/format'
import { motion, AnimatePresence } from 'motion/react'
import { ORDERS_PAGE_LIMIT } from '../config'
import { useTranslation } from '../context/LanguageContext'

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
  const { t } = useTranslation()
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
  const [sortBy, setSortBy] = useState('created_at')
  const [sortDir, setSortDir] = useState('desc')
  const [editModal, setEditModal] = useState(null)
  const [editTable, setEditTable] = useState('')
  const [editAmount, setEditAmount] = useState('')
  const [cancelModal, setCancelModal] = useState(null)
  const limit = ORDERS_PAGE_LIMIT

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

  const refreshOrders = () => getOpsOrders({ ...params, _t: Date.now() }).then(setData)

  useEffect(() => {
    setLoading(true)
    setError('')
    getOpsOrders(params)
      .then(setData)
      .catch((err) => setError(err?.detail || err?.message || 'Failed to load orders'))
      .finally(() => setLoading(false))
  }, [params])

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
    if (!editModal) {
      setEditModal(order)
      setEditTable(order.table_number || '')
      setEditAmount(String(order.total_amount || 0))
      return
    }
    setBusyOrderId(order.order_id)
    setNotice('')
    setError('')
    try {
      const parsedAmount = Number(editAmount)
      if (Number.isNaN(parsedAmount) || parsedAmount < 0) {
        throw new Error('Total amount must be a non-negative number.')
      }
      await updateOpsOrder(order.order_id, {
        table_number: editTable.trim() || null,
        total_amount: parsedAmount,
      })
      setEditModal(null)
      await refreshOrders()
      setNotice(`Order ${formatOrderId(order)} updated.`)
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not update order')
    } finally {
      setBusyOrderId('')
    }
  }

  const submitEditOrder = async () => {
    if (!editModal) return
    setBusyOrderId(editModal.order_id)
    setNotice('')
    setError('')
    try {
      const parsedAmount = Number(editAmount)
      if (Number.isNaN(parsedAmount) || parsedAmount < 0) {
        throw new Error('Total amount must be a non-negative number.')
      }
      await updateOpsOrder(editModal.order_id, {
        table_number: editTable.trim() || null,
        total_amount: parsedAmount,
      })
      const savedOrder = editModal
      setEditModal(null)
      await refreshOrders()
      setNotice(`Order ${formatOrderId(savedOrder)} updated.`)
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not update order')
    } finally {
      setBusyOrderId('')
    }
  }

  const handleCancelOrder = async (order) => {
    if (order.status === 'cancelled') return
    setCancelModal(order)
  }

  const confirmCancelOrder = async () => {
    if (!cancelModal) return
    const order = cancelModal
    setBusyOrderId(order.order_id)
    setNotice('')
    setError('')
    try {
      await cancelOpsOrder(order.order_id)
      setCancelModal(null)
      await refreshOrders()
      setNotice(`Order ${formatOrderId(order)} cancelled.`)
    } catch (err) {
      setError(err?.detail || err?.message || 'Could not cancel order')
    } finally {
      setBusyOrderId('')
    }
  }

  const { summary, orders: rawOrders, total } = data || {}
  const totalPages = Math.max(1, Math.ceil((total || 0) / limit))

  const handleSort = (col) => {
    if (sortBy === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(col)
      setSortDir('asc')
    }
  }

  const sortIndicator = (col) => {
    if (sortBy !== col) return ''
    return sortDir === 'asc' ? ' \u25B2' : ' \u25BC'
  }

  const orders = useMemo(() => {
    if (!rawOrders) return []
    const sorted = [...rawOrders]
    sorted.sort((a, b) => {
      let va = a[sortBy]
      let vb = b[sortBy]
      // Handle nulls
      if (va == null) va = ''
      if (vb == null) vb = ''
      // Numeric columns
      if (sortBy === 'total_amount') {
        va = Number(va) || 0
        vb = Number(vb) || 0
      }
      // String compare
      if (typeof va === 'string') va = va.toLowerCase()
      if (typeof vb === 'string') vb = vb.toLowerCase()
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return sorted
  }, [rawOrders, sortBy, sortDir])

  const hasOrders = orders.length > 0

  if (loading) return <div className="loading">Loading orders...</div>
  if (!data) return <div className="loading">Failed to load orders.</div>

  return (
    <div className="app-page">
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">{t('page_orders_eyebrow')}</div>
          <h1 className="app-hero-title">{t('page_orders_title')}</h1>
          <p className="app-hero-sub">{t('page_orders_sub')}</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <div className="app-hero-metrics">
            <div className="app-kpi">
              <div className="app-kpi-label">{t('page_orders_total_30d')}</div>
              <div className="app-kpi-value">{summary.total_orders}</div>
            </div>
            <div className="app-kpi">
              <div className="app-kpi-label">{t('page_orders_revenue_30d')}</div>
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
            <div className="search-input-wrap">
              <input
                className="input"
                placeholder="Search order id or number"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { setDebouncedSearch(search.trim()); setPage(1) } }}
              />
              {loading && <span className="search-dots"><span /><span /><span /></span>}
            </div>
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
                      <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('order_number')}>Order ID{sortIndicator('order_number')}</th>
                      <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('order_type')}>Type{sortIndicator('order_type')}</th>
                      <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('table_number')}>Table{sortIndicator('table_number')}</th>
                      <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('status')}>Status{sortIndicator('status')}</th>
                      <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('source')}>Source{sortIndicator('source')}</th>
                      <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('total_amount')}>Total{sortIndicator('total_amount')}</th>
                      <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => handleSort('created_at')}>Created{sortIndicator('created_at')}</th>
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

      <AnimatePresence>
        {editModal && (
          <div className="inventory-modal-backdrop" onClick={() => setEditModal(null)}>
            <motion.div
              className="inventory-modal"
              initial={{ opacity: 0, scale: 0.95, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 16 }}
              transition={{ duration: 0.2 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Edit Order {formatOrderId(editModal)}</span>
                <button className="btn btn-ghost" onClick={() => setEditModal(null)}>Close</button>
              </div>
              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                <label style={{ fontSize: 13, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  Table Number
                  <input
                    className="input"
                    placeholder="Leave blank to clear"
                    value={editTable}
                    onChange={(e) => setEditTable(e.target.value)}
                  />
                </label>
                <label style={{ fontSize: 13, display: 'flex', flexDirection: 'column', gap: 6 }}>
                  Total Amount
                  <input
                    className="input"
                    type="number"
                    min="0"
                    step="0.01"
                    value={editAmount}
                    onChange={(e) => setEditAmount(e.target.value)}
                  />
                </label>
                <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end', marginTop: 'var(--space-2)' }}>
                  <button className="btn btn-ghost" onClick={() => setEditModal(null)}>Cancel</button>
                  <button className="btn btn-primary" onClick={submitEditOrder} disabled={!!busyOrderId}>
                    {busyOrderId ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {cancelModal && (
          <div className="inventory-modal-backdrop" onClick={() => setCancelModal(null)}>
            <motion.div
              className="inventory-modal"
              initial={{ opacity: 0, scale: 0.95, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 16 }}
              transition={{ duration: 0.2 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>Cancel Order</span>
                <button className="btn btn-ghost" onClick={() => setCancelModal(null)}>Close</button>
              </div>
              <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  Are you sure you want to cancel order <strong>{formatOrderId(cancelModal)}</strong>? This action cannot be undone.
                </p>
                <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
                  <button className="btn btn-ghost" onClick={() => setCancelModal(null)}>Keep Order</button>
                  <button className="btn btn-primary" style={{ background: 'var(--danger)' }} onClick={confirmCancelOrder} disabled={!!busyOrderId}>
                    {busyOrderId ? 'Cancelling...' : 'Confirm Cancel'}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
