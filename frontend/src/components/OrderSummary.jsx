import { motion } from 'motion/react'

export default function OrderSummary({ order }) {
  if (!order) return null

  return (
    <motion.div
      className="card"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
    >
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>Order Summary</span>
        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{order.order_id}</span>
      </div>
      <div className="card-body">
        {order.items?.map((item, idx) => (
          <motion.div
            key={idx}
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: 'var(--space-2) 0',
              borderBottom: '1px solid var(--border-subtle)',
            }}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.06, duration: 0.3 }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {/* Indian veg indicator */}
              {item.is_veg !== undefined && (
                <span className={item.is_veg ? 'veg-indicator veg' : 'veg-indicator non-veg'} />
              )}
              <div>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {item.quantity}× {item.name}
                </span>
                {/* Modifier chips */}
                {item.modifiers && Object.keys(item.modifiers).some(k => {
                  const v = item.modifiers[k]
                  return v && v !== 'medium' && v !== 'regular' && (Array.isArray(v) ? v.length > 0 : v)
                }) && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 3 }}>
                    {item.modifiers.spice_level && item.modifiers.spice_level !== 'medium' && (
                      <span style={{
                        fontSize: 10, padding: '1px 6px', borderRadius: 'var(--radius-full)',
                        background: 'var(--warning-subtle)', color: 'var(--warning)',
                      }}>🌶️ {item.modifiers.spice_level}</span>
                    )}
                    {item.modifiers.add_ons?.map((a, i) => (
                      <span key={i} style={{
                        fontSize: 10, padding: '1px 6px', borderRadius: 'var(--radius-full)',
                        background: 'var(--bg-overlay)', color: 'var(--text-secondary)',
                      }}>+ {a.replace('_', ' ')}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
              ₹{item.line_total}
            </span>
          </motion.div>
        ))}

        {/* Totals */}
        <motion.div
          style={{ marginTop: 'var(--space-3)', paddingTop: 'var(--space-2)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.5 }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span>Subtotal</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>₹{order.subtotal}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
            <span>GST (5%)</span>
            <span style={{ fontFamily: 'var(--font-mono)' }}>₹{order.tax}</span>
          </div>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            fontSize: 16, fontWeight: 800, fontFamily: 'var(--font-mono)',
            color: 'var(--accent)',
            borderTop: '1px solid var(--border-mid)', paddingTop: 'var(--space-2)',
          }}>
            <span style={{ fontFamily: 'var(--font-body)' }}>Total</span>
            <span>₹{order.total}</span>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}
