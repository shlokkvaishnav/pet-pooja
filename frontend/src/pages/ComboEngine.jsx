import { useEffect, useMemo, useState } from 'react'
import { motion } from 'motion/react'
import { getCombos, getDashboardMetrics, getMenuMatrix } from '../api/client'
import { formatPct, formatRupees } from '../utils/format'
import { buildComboInsights } from '../utils/revenueInsights'

function ComboSkeleton() {
  return (
    <div className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
      {Array.from({ length: 4 }).map((_, idx) => (
        <div key={idx} className="card">
          <div className="card-body">
            <div className="skeleton" style={{ height: 18, marginBottom: 10 }} />
            <div className="skeleton" style={{ height: 12, marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 12, marginBottom: 8 }} />
            <div className="skeleton" style={{ height: 36 }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function ComboEngine() {
  const [loading, setLoading] = useState(true)
  const [combosRaw, setCombosRaw] = useState([])
  const [menuItems, setMenuItems] = useState([])
  const [totalOrders, setTotalOrders] = useState(0)
  const [promotedIds, setPromotedIds] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)

    Promise.all([
      getCombos(),
      getMenuMatrix(),
      getDashboardMetrics(),
    ])
      .then(([comboData, matrixData, dashboard]) => {
        if (!active) return
        setCombosRaw(comboData?.combos || comboData || [])
        setMenuItems(matrixData?.items || [])
        setTotalOrders(dashboard?.total_orders || 0)
      })
      .catch((err) => {
        if (!active) return
        setError(err?.detail || 'Failed to load combo insights')
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  const insights = useMemo(() => buildComboInsights({
    combos: combosRaw,
    menuItems,
    totalOrders,
    promotedIds,
  }), [combosRaw, menuItems, totalOrders, promotedIds])

  const promoteCombo = (id) => {
    setPromotedIds((prev) => (prev.includes(id) ? prev : [...prev, id]))
  }

  if (loading) {
    return (
      <div className="app-page">
        <div className="skeleton" style={{ height: 84, marginBottom: 'var(--space-5)' }} />
        <div className="skeleton" style={{ height: 70, marginBottom: 'var(--space-5)' }} />
        <ComboSkeleton />
        <div className="skeleton" style={{ height: 220 }} />
      </div>
    )
  }

  if (error) {
    return <div className="loading">{error}</div>
  }

  const summary = insights.summary
  const hasCombos = insights.combos.length > 0

  return (
    <motion.div
      className="app-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">Intelligence</div>
          <h1 className="app-hero-title">Combo Engine</h1>
          <p className="app-hero-sub">AI-generated bundles to increase average order value and margin contribution.</p>
        </div>
      </div>

      {insights.usedSynthetic && (
        <div className="card" style={{ marginBottom: 'var(--space-4)', borderColor: 'var(--warning)' }}>
          <div className="card-body" style={{ fontSize: 13 }}>
            Limited order history detected (under 30 records). Showing realistic demo combos from a display-only synthetic model.
          </div>
        </div>
      )}

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: 'var(--space-3)',
          marginBottom: 'var(--space-5)',
        }}
      >
        <div className="card"><div className="card-body"><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Total Combos Identified</div><div style={{ fontSize: 28, fontWeight: 800 }}>{summary.totalCombos}</div></div></div>
        <div className="card"><div className="card-body"><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Average AOV Uplift</div><div style={{ fontSize: 28, fontWeight: 800, color: 'var(--accent)' }}>{formatPct(summary.avgAovUpliftPct)}</div></div></div>
        <div className="card"><div className="card-body"><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Active / Promoted</div><div style={{ fontSize: 28, fontWeight: 800, color: 'var(--success)' }}>{summary.activePromoted}</div></div></div>
      </section>

      <section style={{ marginBottom: 'var(--space-6)' }}>
        <h2 style={{ marginBottom: 'var(--space-3)' }}>Recommended Combos</h2>
        {!hasCombos ? (
          <div className="card">
            <div className="card-body">
              Unable to compute combos right now. Refresh after new order data is available.
            </div>
          </div>
        ) : (
          <div className="grid-2">
            {insights.combos.map((combo) => (
              <div key={combo.id} className="card">
                <div className="card-body">
                  <div style={{ fontWeight: 700, marginBottom: 8 }}>{combo.itemNames.join(' + ')}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 10 }}>
                    {combo.itemNames.map((name, idx) => `${name} (${formatRupees(combo.itemPrices[idx] || 0)})`).join('  |  ')}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
                    <div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Combined Price</div><div style={{ fontWeight: 700 }}>{formatRupees(combo.combinedPrice)}</div></div>
                    <div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Bundle Price</div><div style={{ fontWeight: 700, color: 'var(--success)' }}>{formatRupees(combo.bundlePrice)}</div></div>
                    <div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Discount</div><div style={{ fontWeight: 700 }}>{formatPct(combo.discountPct)}</div></div>
                    <div><div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Est. AOV Uplift</div><div style={{ fontWeight: 700, color: 'var(--accent)' }}>+{formatPct(combo.aovUpliftPct)}</div></div>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Confidence: <strong>{formatPct(combo.confidence * 100)}</strong> based on order co-occurrence frequency.
                  </div>
                  <button
                    className={combo.isPromoted ? 'btn btn-secondary' : 'btn btn-primary'}
                    onClick={() => promoteCombo(combo.id)}
                    disabled={combo.isPromoted}
                    style={{ width: '100%' }}
                  >
                    {combo.isPromoted ? 'Promoted' : 'Promote This Combo'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 style={{ marginBottom: 'var(--space-3)' }}>Promoted Combo Performance</h2>
        {insights.promotedPerformance.length === 0 ? (
          <div className="card">
            <div className="card-body">
              Promote at least one combo to start tracking performance metrics.
            </div>
          </div>
        ) : (
          <div className="card">
            <div className="card-body" style={{ padding: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Combo Name</th>
                    <th style={{ textAlign: 'right' }}>Times Suggested</th>
                    <th style={{ textAlign: 'right' }}>Times Accepted</th>
                    <th style={{ textAlign: 'right' }}>Acceptance Rate</th>
                    <th style={{ textAlign: 'right' }}>Revenue Attributed</th>
                  </tr>
                </thead>
                <tbody>
                  {insights.promotedPerformance.map((row) => (
                    <tr key={row.id}>
                      <td style={{ fontWeight: 600 }}>{row.comboName}</td>
                      <td className="col-number">{row.timesSuggested}</td>
                      <td className="col-number">{row.timesAccepted}</td>
                      <td className="col-number">{formatPct(row.acceptanceRate)}</td>
                      <td className="col-number">{formatRupees(row.revenueAttributed)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </motion.div>
  )
}

