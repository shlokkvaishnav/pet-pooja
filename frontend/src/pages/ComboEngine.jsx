import { useState, useEffect } from 'react'
import { getCombos, getPriceRecommendations } from '../api/client'
import ComboCard from '../components/ComboCard'
import { motion } from 'motion/react'
import { StaggerReveal, ScrollReveal, staggerContainer, staggerItem, fadeInUp } from '../utils/animations'

export default function ComboEngine() {
  const [combos, setCombos] = useState([])
  const [prices, setPrices] = useState([])
  const [loading, setLoading] = useState(true)
  const [retraining, setRetraining] = useState(false)
  const [discountPct, setDiscountPct] = useState(10)

  const loadData = (forceRetrain = false) => {
    const setLoadingFn = forceRetrain ? setRetraining : setLoading
    setLoadingFn(true)

    Promise.all([
      getCombos(forceRetrain, discountPct).catch(() => ({ combos: [] })),
      forceRetrain ? Promise.resolve(null) : getPriceRecommendations().catch(() => [])
    ])
      .then(([comboData, priceData]) => {
        setCombos(comboData.combos || comboData || [])
        if (priceData) setPrices(priceData || [])
      })
      .catch(err => console.error('Combos/Pricing failed:', err))
      .finally(() => setLoadingFn(false))
  }

  useEffect(() => { loadData() }, [])

  if (loading) {
    return <div className="loading"><div className="spinner" /> Mining combos and crunching prices...</div>
  }

  const avgLift = combos.length > 0 ? (combos.reduce((s, c) => s + (parseFloat(c.lift) || 0), 0) / combos.length).toFixed(1) : '—'
  const avgConf = combos.length > 0 ? (combos.reduce((s, c) => s + (c.confidence || 0), 0) / combos.length * 100).toFixed(0) : '—'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div
        className="page-header"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 style={{ fontFamily: 'var(--font-display)' }}>Combo Intelligence</h1>
        <p>AI-generated combo recommendations & quadrant-based price strategies</p>
      </motion.div>

      {/* Summary bar */}
      <div style={{
        display: 'flex', gap: 'var(--space-6)', alignItems: 'center',
        padding: 'var(--space-3) var(--space-5)',
        background: 'var(--bg-surface)', borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)', marginBottom: 'var(--space-6)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>{combos.length}</span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Combos</span>
        </div>
        <div style={{ width: 1, height: 24, background: 'var(--border-subtle)' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: 'var(--accent)' }}>{avgLift}×</span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Avg Lift</span>
        </div>
        <div style={{ width: 1, height: 24, background: 'var(--border-subtle)' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700, color: 'var(--success)' }}>{avgConf}%</span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Avg Confidence</span>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
            Discount
            <input
              type="number"
              min="1"
              max="30"
              value={discountPct}
              onChange={e => setDiscountPct(Number(e.target.value))}
              style={{ width: 48 }}
            />
            <span>%</span>
          </label>
          <button
            className="btn btn-secondary"
            onClick={() => loadData(true)}
            disabled={retraining}
            style={{ padding: '6px 14px', fontSize: 12 }}
          >
            {retraining ? 'Retraining…' : 'Retrain Model'}
          </button>
        </div>
      </div>

      {/* Combos */}
      {combos.length === 0 ? (
        <div className="card" style={{ marginBottom: 32 }}>
          <div className="card-body" style={{ textAlign: 'center', padding: 40 }}>
            <p style={{ color: 'var(--text-muted)' }}>No combos generated yet.</p>
          </div>
        </div>
      ) : (
        <StaggerReveal className="grid-2" style={{ marginBottom: 32 }} variants={staggerContainer}>
          {combos.map((combo, idx) => (
            <motion.div key={idx} variants={staggerItem}>
              <ComboCard combo={combo} />
            </motion.div>
          ))}
        </StaggerReveal>
      )}

      {/* Price Recommendations */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 'var(--space-4)' }}>
        <h2 style={{ fontSize: 18, fontFamily: 'var(--font-display)', margin: 0 }}>Price Recommendations</h2>
        {prices.length > 0 && (
          <span style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 'var(--radius-full)',
            background: 'var(--bg-overlay)', color: 'var(--text-secondary)',
          }}>{prices.length} items</span>
        )}
      </div>

      <ScrollReveal variants={fadeInUp}>
        <div className="card">
          <div className="card-body" style={{ padding: 0 }}>
            {prices.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                No price recommendations at this time.
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th style={{ textAlign: 'right' }}>Current</th>
                    <th style={{ textAlign: 'right' }}>Suggested</th>
                    <th>Strategy</th>
                    <th>Reasoning</th>
                  </tr>
                </thead>
                <tbody>
                  {prices.map((p, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{p.name}</td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)' }}>₹{p.current_price}</td>
                      <td style={{
                        textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600,
                        color: p.suggested_price > p.current_price ? 'var(--success)' : 'var(--text-primary)'
                      }}>
                        ₹{p.suggested_price}
                        {p.suggested_price > p.current_price && <span style={{ fontSize: 11, marginLeft: 4 }}>↑</span>}
                      </td>
                      <td>
                        <span className={`tag tag-${p.priority === 'high' ? 'red' : p.priority === 'medium' ? 'amber' : 'blue'}`}>
                          {p.quadrant?.replace('_', ' ')}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{p.reasoning}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </ScrollReveal>
    </motion.div>
  )
}
