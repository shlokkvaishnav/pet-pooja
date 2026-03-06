import { motion } from 'motion/react'

export default function KOTTicket({ kot }) {
  if (!kot) return null

  return (
    <motion.div
      className="kot-ticket"
      initial={{ opacity: 0, y: 30, scaleY: 0.8 }}
      animate={{ opacity: 1, y: 0, scaleY: 1 }}
      transition={{ duration: 0.5, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Header */}
      <div style={{
        textAlign: 'center', padding: 'var(--space-4)',
        borderBottom: '2px dashed var(--border-subtle)',
      }}>
        <div style={{
          fontSize: 11, fontFamily: 'var(--font-body)', textTransform: 'uppercase',
          letterSpacing: '0.12em', color: 'var(--text-muted)', marginBottom: 4,
        }}>
          Kitchen Order Ticket
        </div>
        <div style={{ fontSize: 18, fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent)' }}>
          {kot.kot_id}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
          {kot.order_type?.toUpperCase()} • Table: {kot.table || '-'}
        </div>
        <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
          {kot.timestamp}
        </div>
      </div>

      {/* Items */}
      <div style={{ padding: 'var(--space-3) var(--space-4)' }}>
        {kot.items?.map((item, idx) => (
          <motion.div
            key={idx}
            style={{ marginBottom: 'var(--space-2)' }}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 + idx * 0.08, duration: 0.3 }}
          >
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              fontSize: 14, fontFamily: 'var(--font-mono)', fontWeight: 700,
              color: 'var(--text-primary)',
            }}>
              <span>{item.name}</span>
              <span>×{item.qty}</span>
            </div>
            {item.modifiers?.length > 0 && (
              <div style={{ fontSize: 11, color: 'var(--warning)', paddingLeft: 8, fontFamily: 'var(--font-body)' }}>
                → {item.modifiers.join(', ')}
              </div>
            )}
            {item.notes && (
              <div style={{ fontSize: 11, color: 'var(--danger)', paddingLeft: 8, fontFamily: 'var(--font-body)' }}>
                ★ {item.notes}
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Footer */}
      <motion.div
        style={{
          borderTop: '2px dashed var(--border-subtle)',
          padding: 'var(--space-3) var(--space-4)',
          textAlign: 'center',
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.4 }}
      >
        <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
          Total items: {kot.total_items}
        </div>
        <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          Powered by Sizzle
        </div>
      </motion.div>
    </motion.div>
  )
}
