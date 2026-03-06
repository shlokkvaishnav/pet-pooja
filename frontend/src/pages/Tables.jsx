import { useEffect, useMemo, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  getOpsTablesFiltered,
  bookTable,
  settleTable,
  reserveTable,
  unreserveTable,
  seatReservedTable,
  getMenuItemsList,
  addItemToTableOrder,
} from '../api/client'

const statusStyles = {
  empty: { color: '#2A7A50', bg: 'var(--success-subtle)', label: 'Available' },
  occupied: { color: '#C07A20', bg: 'var(--warning-subtle)', label: 'Occupied' },
  reserved: { color: '#2A5A8C', bg: 'var(--info-subtle)', label: 'Reserved' },
  cleaning: { color: '#7A7A84', bg: 'rgba(122, 122, 132, 0.15)', label: 'Needs Cleaning' },
}

function formatOrderRef(table) {
  if (!table.current_order_id) return 'N/A'
  const compact = String(table.current_order_id).replace(/-/g, '').toUpperCase()
  return `#${compact.slice(0, 8)}`
}

function formatSeatedTime(table) {
  const value = table.seated_at || table.updated_at || table.created_at
  if (!value || table.status === 'empty') return 'Not seated'
  const dt = new Date(value)
  if (Number.isNaN(dt.valueOf())) return 'Unknown'
  return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/* ── Settle Bill Modal ── */
function SettleModal({ table, onClose, onSettle }) {
  const [method, setMethod] = useState('cash')
  const [settling, setSettling] = useState(false)

  const handleSettle = async () => {
    setSettling(true)
    try {
      await onSettle(table.table_id, method)
      onClose()
    } catch (err) {
      console.error(err)
    } finally {
      setSettling(false)
    }
  }

  const order = table.order
  const items = order?.items || []

  return (
    <div className="tbl-modal-overlay" onClick={onClose}>
      <motion.div
        className="tbl-modal"
        initial={{ opacity: 0, scale: 0.95, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 16 }}
        transition={{ duration: 0.2 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="tbl-modal-header">
          <h3>Settle Bill — Table {table.table_number}</h3>
          <button className="tbl-modal-close" onClick={onClose}>×</button>
        </div>
        <div className="tbl-modal-body">
          {items.length > 0 ? (
            <div className="tbl-bill-items">
              <div className="tbl-bill-row tbl-bill-head">
                <span>Item</span>
                <span>Qty</span>
                <span>Price</span>
                <span>Total</span>
              </div>
              {items.map((item, i) => (
                <div className="tbl-bill-row" key={i}>
                  <span>{item.name}</span>
                  <span>{item.quantity}</span>
                  <span>₹{item.unit_price?.toFixed(0)}</span>
                  <span>₹{item.line_total?.toFixed(0)}</span>
                </div>
              ))}
              <div className="tbl-bill-row tbl-bill-total">
                <span>Total</span>
                <span></span>
                <span></span>
                <span>₹{order?.total_amount?.toFixed(0) || '0'}</span>
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 'var(--space-6)' }}>
              No items on this order yet.
            </p>
          )}

          <div className="tbl-payment-methods">
            <label className="tbl-payment-label">Payment Method</label>
            <div className="tbl-payment-options">
              {['cash', 'card', 'upi'].map((m) => (
                <button
                  key={m}
                  className={`tbl-payment-btn ${method === m ? 'active' : ''}`}
                  onClick={() => setMethod(m)}
                >
                  {m === 'cash' ? '💵' : m === 'card' ? '💳' : '📱'} {m.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="tbl-modal-footer">
          <button className="btn btn-ghost" onClick={onClose} disabled={settling}>Cancel</button>
          <button
            className="tbl-settle-confirm-btn"
            onClick={handleSettle}
            disabled={settling}
          >
            {settling ? 'Processing...' : `Settle ₹${order?.total_amount?.toFixed(0) || '0'}`}
          </button>
        </div>
      </motion.div>
    </div>
  )
}

/* ── Add Item Modal ── */
function AddItemModal({ table, onClose, onItemAdded }) {
  const [menuItems, setMenuItems] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(null)
  const [addedItems, setAddedItems] = useState({}) // itemId -> true (brief success flash)
  const [addError, setAddError] = useState(null)

  useEffect(() => {
    setLoading(true)
    getMenuItemsList(search)
      .then((d) => setMenuItems(d.items || []))
      .finally(() => setLoading(false))
  }, [search])

  const handleAdd = async (itemId) => {
    setAdding(itemId)
    setAddError(null)
    try {
      await addItemToTableOrder(table.table_id, itemId, 1)
      setAddedItems((prev) => ({ ...prev, [itemId]: true }))
      setTimeout(() => setAddedItems((prev) => { const n = { ...prev }; delete n[itemId]; return n }), 1500)
      onItemAdded()
    } catch (err) {
      setAddError(err?.detail || 'Failed to add item')
    } finally {
      setAdding(null)
    }
  }

  return (
    <div className="tbl-modal-overlay" onClick={onClose}>
      <motion.div
        className="tbl-modal tbl-modal-lg"
        initial={{ opacity: 0, scale: 0.95, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 16 }}
        transition={{ duration: 0.2 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="tbl-modal-header">
          <h3>Add Items — Table {table.table_number}</h3>
          <button className="tbl-modal-close" onClick={onClose}>×</button>
        </div>
        <div className="tbl-modal-body">
          <input
            className="input"
            placeholder="Search menu items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ marginBottom: 'var(--space-4)' }}
            autoFocus
          />
          {addError && (
            <div style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 'var(--space-3)', padding: '6px 10px', background: 'var(--danger-subtle)', borderRadius: 'var(--radius-sm)' }}>
              {addError}
            </div>
          )}
          {loading ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--text-muted)' }}>Loading...</div>
          ) : menuItems.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--text-muted)' }}>No items found.</div>
          ) : (
            <div className="tbl-menu-grid">
              {menuItems.map((item) => (
                <div key={item.id} className="tbl-menu-item">
                  <div className="tbl-menu-item-info">
                    <span className={`tbl-veg-dot ${item.is_veg ? 'veg' : 'non-veg'}`} />
                    <div>
                      <div className="tbl-menu-item-name">{item.name}</div>
                      <div className="tbl-menu-item-cat">{item.category}</div>
                    </div>
                  </div>
                  <div className="tbl-menu-item-right">
                    <span className="tbl-menu-item-price">₹{item.price?.toFixed(0)}</span>
                    <button
                      className="tbl-add-btn"
                      onClick={() => handleAdd(item.id)}
                      disabled={adding === item.id}
                      style={addedItems[item.id] ? { background: 'var(--success)', color: '#fff' } : undefined}
                    >
                      {adding === item.id ? '...' : addedItems[item.id] ? '✓' : '+'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="tbl-modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Done</button>
        </div>
      </motion.div>
    </div>
  )
}

/* ── Main Tables Component ── */
export default function Tables() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [sectionFilter, setSectionFilter] = useState('')
  const [search, setSearch] = useState('')
  const [viewMode, setViewMode] = useState('floor')
  const [selectedTableId, setSelectedTableId] = useState(null)
  const [settleTarget, setSettleTarget] = useState(null)
  const [addItemTarget, setAddItemTarget] = useState(null)
  const [actionLoading, setActionLoading] = useState({})
  const [toast, setToast] = useState(null)

  const params = useMemo(
    () => ({
      status: statusFilter || undefined,
      section: sectionFilter || undefined,
      search: search || undefined,
    }),
    [statusFilter, sectionFilter, search],
  )

  const reload = useCallback(() => {
    setLoading(true)
    getOpsTablesFiltered(params)
      .then(setData)
      .finally(() => setLoading(false))
  }, [params])

  useEffect(() => { reload() }, [reload])

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  const setTableAction = (id, isLoading) => setActionLoading((prev) => ({ ...prev, [id]: isLoading }))

  /* ── Actions ── */
  const handleBook = async (tableId) => {
    setTableAction(tableId, true)
    try {
      await bookTable(tableId)
      showToast('Table booked successfully')
      reload()
    } catch (err) {
      showToast(err?.detail || 'Failed to book table', 'error')
    } finally {
      setTableAction(tableId, false)
    }
  }

  const handleReserve = async (tableId) => {
    setTableAction(tableId, true)
    try {
      await reserveTable(tableId)
      showToast('Table reserved')
      reload()
    } catch (err) {
      showToast(err?.detail || 'Failed to reserve', 'error')
    } finally {
      setTableAction(tableId, false)
    }
  }

  const handleUnreserve = async (tableId) => {
    setTableAction(tableId, true)
    try {
      await unreserveTable(tableId)
      showToast('Reservation removed')
      reload()
    } catch (err) {
      showToast(err?.detail || 'Failed to unreserve', 'error')
    } finally {
      setTableAction(tableId, false)
    }
  }

  const handleSeat = async (tableId) => {
    setTableAction(tableId, true)
    try {
      await seatReservedTable(tableId)
      showToast('Guests seated')
      reload()
    } catch (err) {
      showToast(err?.detail || 'Failed to seat', 'error')
    } finally {
      setTableAction(tableId, false)
    }
  }

  const handleSettle = async (tableId, paymentMethod) => {
    try {
      const res = await settleTable(tableId, { payment_method: paymentMethod })
      showToast(`Bill settled — ₹${res.total_amount} via ${paymentMethod}`)
      reload()
    } catch (err) {
      showToast(err?.detail || 'Failed to settle bill', 'error')
    }
  }

  if (loading && !data) {
    return (
      <div className="app-page">
        <div style={{ padding: 'var(--space-12)' }}>
          <div className="tables-floor-grid">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="skeleton" style={{ height: 200, borderRadius: 'var(--radius-lg)', animationDelay: `${i * 60}ms` }} />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (!data) return <div className="loading">Failed to load tables.</div>

  const { summary, tables } = data
  const hasTables = tables.length > 0
  const sectionOptions = Array.from(new Set(tables.map((table) => table.section).filter(Boolean)))
  const selectedTable = tables.find((table) => table.table_id === selectedTableId) || null

  return (
    <motion.div
      className="app-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      {/* Hero */}
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">Operations</div>
          <h1 className="app-hero-title">Tables</h1>
          <p className="app-hero-sub">Visual floor plan and live table management.</p>
        </div>
        <div className="app-hero-metrics">
          <div className="app-kpi">
            <div className="app-kpi-label">Total</div>
            <div className="app-kpi-value">{summary.total_tables}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label" style={{ color: statusStyles.empty.color }}>Available</div>
            <div className="app-kpi-value" style={{ color: statusStyles.empty.color }}>{summary.empty || 0}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label" style={{ color: statusStyles.occupied.color }}>Occupied</div>
            <div className="app-kpi-value" style={{ color: statusStyles.occupied.color }}>{summary.occupied || 0}</div>
          </div>
          <div className="app-kpi">
            <div className="app-kpi-label" style={{ color: statusStyles.reserved.color }}>Reserved</div>
            <div className="app-kpi-value" style={{ color: statusStyles.reserved.color }}>{summary.reserved || 0}</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-header">Floor Controls</div>
        <div className="card-body">
          <div className="tables-toolbar">
            <div className="filters-row tables-filters-row">
              <input
                className="input"
                placeholder="Search table number"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <select className="input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="">All Statuses</option>
                <option value="empty">Available</option>
                <option value="occupied">Occupied</option>
                <option value="reserved">Reserved</option>
                <option value="cleaning">Needs Cleaning</option>
              </select>
              <select className="input" value={sectionFilter} onChange={(e) => setSectionFilter(e.target.value)}>
                <option value="">All Sections</option>
                {sectionOptions.map((sectionName) => (
                  <option key={sectionName} value={sectionName}>
                    {sectionName}
                  </option>
                ))}
              </select>
            </div>
            <div className="tables-view-toggle">
              <button
                className={`btn ${viewMode === 'floor' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setViewMode('floor')}
              >
                Floor Plan
              </button>
              <button
                className={`btn ${viewMode === 'list' ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setViewMode('list')}
              >
                List View
              </button>
            </div>
          </div>
        </div>
      </div>

      {!hasTables ? (
        <div className="card">
          <div className="card-body">
            <div className="tables-empty-state">
              <div className="tables-empty-icon">🪑</div>
              <h3>No tables configured</h3>
              <p>Add tables in setup to start managing occupancy and reservations.</p>
            </div>
          </div>
        </div>
      ) : viewMode === 'floor' ? (
        <div className="tables-floor-grid">
          {tables.map((table) => {
            const style = statusStyles[table.status] || statusStyles.empty
            const isLoading = actionLoading[table.table_id]
            const order = table.order

            return (
              <motion.div
                key={table.table_id}
                className={`tables-floor-card ${selectedTableId === table.table_id ? 'tables-floor-card--active' : ''}`}
                style={{ '--table-accent': style.color, cursor: 'pointer' }}
                onClick={() => setSelectedTableId(table.table_id)}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="tables-floor-card-head">
                  <strong>Table {table.table_number}</strong>
                  <span className="status-pill" style={{ color: style.color, borderColor: style.color, background: style.bg }}>
                    {style.label}
                  </span>
                </div>
                <div className="tables-floor-card-meta">
                  <span>{table.capacity}-seater</span>
                  <span>{table.section || 'Main Hall'}</span>
                </div>
                <div className="tables-floor-card-meta">
                  <span>Order: {formatOrderRef(table)}</span>
                  <span>Seated: {formatSeatedTime(table)}</span>
                </div>

                {/* Order items preview for occupied tables */}
                {table.status === 'occupied' && order && order.items && order.items.length > 0 && (
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
                    {order.items.slice(0, 2).map((item, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>{item.quantity}× {item.name}</span>
                        <span>₹{item.line_total?.toFixed(0)}</span>
                      </div>
                    ))}
                    {order.items.length > 2 && (
                      <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>+{order.items.length - 2} more</div>
                    )}
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>
                      Total: ₹{order.total_amount?.toFixed(0) || '0'}
                    </div>
                  </div>
                )}

                {/* Dynamic action buttons based on status */}
                <div className="tables-floor-card-actions" onClick={(event) => event.stopPropagation()}>
                  {table.status === 'empty' && (
                    <>
                      <button className="btn btn-primary" onClick={() => handleBook(table.table_id)} disabled={isLoading}>
                        {isLoading ? 'Booking...' : 'Book'}
                      </button>
                      <button className="btn btn-ghost" onClick={() => handleReserve(table.table_id)} disabled={isLoading}>
                        Reserve
                      </button>
                    </>
                  )}
                  {table.status === 'occupied' && (
                    <>
                      <button className="btn btn-ghost" onClick={() => setAddItemTarget(table)} disabled={isLoading}>
                        + Items
                      </button>
                      <button className="btn btn-primary" onClick={() => setSettleTarget(table)} disabled={isLoading}>
                        Settle Bill
                      </button>
                    </>
                  )}
                  {table.status === 'reserved' && (
                    <>
                      <button className="btn btn-primary" onClick={() => handleSeat(table.table_id)} disabled={isLoading}>
                        {isLoading ? 'Seating...' : 'Seat Guests'}
                      </button>
                      <button className="btn btn-ghost" onClick={() => handleUnreserve(table.table_id)} disabled={isLoading}>
                        Cancel
                      </button>
                    </>
                  )}
                  {table.status === 'cleaning' && (
                    <button className="btn btn-ghost" style={{ flex: 1 }} onClick={() => handleBook(table.table_id)} disabled={isLoading}>
                      Mark Available
                    </button>
                  )}
                </div>
              </motion.div>
            )
          })}
        </div>
      ) : (
        <div className="card">
          <div className="card-header">Table List</div>
          <div className="card-body" style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Table</th>
                  <th>Section</th>
                  <th>Capacity</th>
                  <th>Status</th>
                  <th>Current Order</th>
                  <th>Time Seated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tables.map((table) => {
                  const style = statusStyles[table.status] || statusStyles.empty
                  const isLoading = actionLoading[table.table_id]
                  return (
                    <tr key={table.table_id}>
                      <td style={{ fontWeight: 700 }}>Table {table.table_number}</td>
                      <td>{table.section || 'Main Hall'}</td>
                      <td>{table.capacity}</td>
                      <td>
                        <span className="status-pill" style={{ color: style.color, borderColor: style.color, background: style.bg }}>
                          {style.label}
                        </span>
                      </td>
                      <td>{formatOrderRef(table)}</td>
                      <td>{formatSeatedTime(table)}</td>
                      <td>
                        <div className="orders-row-actions">
                          {table.status === 'empty' && (
                            <>
                              <button className="btn btn-ghost" onClick={() => handleBook(table.table_id)} disabled={isLoading}>Book</button>
                              <button className="btn btn-ghost" onClick={() => handleReserve(table.table_id)} disabled={isLoading}>Reserve</button>
                            </>
                          )}
                          {table.status === 'occupied' && (
                            <>
                              <button className="btn btn-ghost" onClick={() => setAddItemTarget(table)} disabled={isLoading}>+ Items</button>
                              <button className="btn btn-ghost" onClick={() => setSettleTarget(table)} disabled={isLoading}>Settle</button>
                            </>
                          )}
                          {table.status === 'reserved' && (
                            <>
                              <button className="btn btn-ghost" onClick={() => handleSeat(table.table_id)} disabled={isLoading}>Seat</button>
                              <button className="btn btn-ghost" onClick={() => handleUnreserve(table.table_id)} disabled={isLoading}>Cancel</button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Table Drawer (incoming UI) */}
      {selectedTable ? (
        <div className="tables-drawer-backdrop" onClick={() => setSelectedTableId(null)}>
          <aside className="tables-drawer" onClick={(event) => event.stopPropagation()}>
            <div className="tables-drawer-head">
              <div>
                <h3>Table {selectedTable.table_number}</h3>
                <p>{selectedTable.section || 'Main Hall'} section</p>
              </div>
              <button className="btn btn-ghost" onClick={() => setSelectedTableId(null)}>Close</button>
            </div>
            <div className="tables-drawer-meta">
              <div><span>Capacity</span><strong>{selectedTable.capacity} seats</strong></div>
              <div><span>Status</span><strong>{(statusStyles[selectedTable.status] || statusStyles.empty).label}</strong></div>
              <div><span>Current Order</span><strong>{formatOrderRef(selectedTable)}</strong></div>
            </div>

            {/* Order details in drawer for occupied tables */}
            {selectedTable.status === 'occupied' && selectedTable.order && (
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-3)' }}>
                <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Order Items</strong>
                {(selectedTable.order.items || []).map((item, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-secondary)', padding: '4px 0' }}>
                    <span>{item.quantity}× {item.name}</span>
                    <span>₹{item.line_total?.toFixed(0)}</span>
                  </div>
                ))}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: 'var(--text-primary)', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
                  <span>Total</span>
                  <span>₹{selectedTable.order.total_amount?.toFixed(0) || '0'}</span>
                </div>
              </div>
            )}

            {/* Dynamic drawer actions based on status */}
            <div className="tables-drawer-actions">
              {selectedTable.status === 'empty' && (
                <>
                  <button className="btn btn-primary" onClick={() => { handleBook(selectedTable.table_id); setSelectedTableId(null) }}>Book Table</button>
                  <button className="btn btn-ghost" onClick={() => { handleReserve(selectedTable.table_id); setSelectedTableId(null) }}>Reserve</button>
                </>
              )}
              {selectedTable.status === 'occupied' && (
                <>
                  <button className="btn btn-ghost" onClick={() => { setAddItemTarget(selectedTable); setSelectedTableId(null) }}>+ Add Items</button>
                  <button className="btn btn-primary" onClick={() => { setSettleTarget(selectedTable); setSelectedTableId(null) }}>Settle Bill</button>
                </>
              )}
              {selectedTable.status === 'reserved' && (
                <>
                  <button className="btn btn-primary" onClick={() => { handleSeat(selectedTable.table_id); setSelectedTableId(null) }}>Seat Guests</button>
                  <button className="btn btn-ghost" onClick={() => { handleUnreserve(selectedTable.table_id); setSelectedTableId(null) }}>Cancel Reservation</button>
                </>
              )}
            </div>
          </aside>
        </div>
      ) : null}

      {/* Settle Modal */}
      <AnimatePresence>
        {settleTarget && (
          <SettleModal
            table={settleTarget}
            onClose={() => setSettleTarget(null)}
            onSettle={handleSettle}
          />
        )}
      </AnimatePresence>

      {/* Add Item Modal */}
      <AnimatePresence>
        {addItemTarget && (
          <AddItemModal
            table={addItemTarget}
            onClose={() => { setAddItemTarget(null); reload() }}
            onItemAdded={reload}
          />
        )}
      </AnimatePresence>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            className={`tbl-toast ${toast.type === 'error' ? 'tbl-toast-error' : ''}`}
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 40 }}
            transition={{ duration: 0.25 }}
          >
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
