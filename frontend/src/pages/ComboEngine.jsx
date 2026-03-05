import { useState, useEffect } from 'react'
import { getCombos, getPriceRecommendations } from '../api/client'
import ComboCard from '../components/ComboCard'

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

  return (
    <div>
      <div className="page-header">
        <h1>Combo Engine & Price Optimizer</h1>
        <p>AI-generated combo recommendations & quadrant-based price strategies</p>
      </div>

      {/* Combo Controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, margin: 0 }}>🔗 Suggested Combos</h2>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Discount %:
            <input
              type="number"
              min="1"
              max="30"
              value={discountPct}
              onChange={e => setDiscountPct(Number(e.target.value))}
              style={{
                width: 50, marginLeft: 4, padding: '4px 6px',
                background: 'var(--surface2)', border: '1px solid var(--border)',
                color: 'var(--text)', borderRadius: 4, fontSize: 13,
              }}
            />
          </label>
          <button
            className="btn btn-secondary"
            onClick={() => loadData(true)}
            disabled={retraining}
            style={{ padding: '6px 12px', fontSize: 13 }}
          >
            {retraining ? '⏳ Retraining...' : '🔄 Retrain Model'}
          </button>
        </div>
      </div>

      {combos.length === 0 ? (
        <div className="card" style={{ marginBottom: 32 }}>
          <div className="card-body" style={{ textAlign: 'center', padding: 40 }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>🔗</div>
            <p style={{ color: 'var(--text-muted)' }}>No combos generated yet.</p>
          </div>
        </div>
      ) : (
        <div className="grid-2" style={{ marginBottom: 32 }}>
          {combos.map((combo, idx) => (
            <ComboCard key={idx} combo={combo} />
          ))}
        </div>
      )}

      <h2 style={{ fontSize: 18, marginBottom: 16 }}>📈 Price Recommendations</h2>
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
                  <th>Current Price</th>
                  <th>Suggested Price</th>
                  <th>Quadrant Strategy</th>
                  <th>Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {prices.map((p, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600 }}>{p.name}</td>
                    <td>₹{p.current_price}</td>
                    <td style={{ fontWeight: 600, color: p.suggested_price > p.current_price ? 'var(--green)' : 'var(--text)' }}>
                      ₹{p.suggested_price}
                      {p.suggested_price > p.current_price && <span style={{ fontSize: 11, marginLeft: 4 }}>↑</span>}
                    </td>
                    <td>
                      <span className={`tag tag-${p.priority === 'high' ? 'red' :
                          p.priority === 'medium' ? 'amber' :
                            'blue'
                        }`}>
                        {p.quadrant?.replace('_', ' ')}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{p.reasoning}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
