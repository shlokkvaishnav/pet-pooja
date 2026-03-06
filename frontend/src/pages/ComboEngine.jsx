import { useEffect, useMemo, useState, useCallback } from 'react'
import { motion } from 'motion/react'
import { getCombos, getDashboardMetrics, getMenuMatrix, promoteCombo as promoteComboApi } from '../api/client'
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
  const [refreshing, setRefreshing] = useState(false)
  const [combosRaw, setCombosRaw] = useState([])
  const [menuItems, setMenuItems] = useState([])
  const [totalOrders, setTotalOrders] = useState(0)
  const [promotedIds, setPromotedIds] = useState([])
  const [error, setError] = useState(null)

  const loadCombos = useCallback((forceRetrain = false) => {
    setError(null)
    if (forceRetrain) setRefreshing(true)
    else setLoading(true)

    Promise.all([
      getCombos(forceRetrain),
      getMenuMatrix(),
      getDashboardMetrics(),
    ])
      .then(([comboData, matrixData, dashboard]) => {
        setCombosRaw(comboData?.combos || comboData || [])
        setMenuItems(matrixData?.items || [])
        setTotalOrders(dashboard?.total_orders || 0)
      })
      .catch((err) => {
        setError(err?.detail || 'Failed to load combo insights')
      })
      .finally(() => {
        setLoading(false)
        setRefreshing(false)
      })
  }, [])

  useEffect(() => {
    loadCombos()
  }, [loadCombos])

  const insights = useMemo(() => buildComboInsights({
    combos: combosRaw,
    menuItems,
    totalOrders,
    promotedIds,
  }), [combosRaw, menuItems, totalOrders, promotedIds])

  const handlePromoteCombo = async (id, comboName) => {
    try {
      await promoteComboApi(id)
      setPromotedIds((prev) => (prev.includes(id) ? prev : [...prev, id]))
      alert(`Successfully promoted: ${comboName}. It is now added to the actual menu in the database!`)
    } catch (err) {
      alert(`Failed to promote combo. ${err?.response?.data?.detail || err.message}`)
    }
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
        <button
          className="btn btn-secondary"
          onClick={() => loadCombos(true)}
          disabled={refreshing}
          style={{ whiteSpace: 'nowrap', alignSelf: 'center' }}
        >
          {refreshing ? 'Retraining…' : '⟳ Refresh Combos'}
        </button>
      </div>

      {insights.insufficientData && (
        <div className="card" style={{ marginBottom: 'var(--space-4)', borderColor: 'var(--warning)' }}>
          <div className="card-body" style={{ fontSize: 13 }}>
            Limited order history detected (under 30 records). Combo recommendations will improve as more orders are placed.
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
            <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span>No combos found yet. Click Refresh to run the correlation analysis now.</span>
              <button className="btn btn-primary" onClick={() => loadCombos(true)} disabled={refreshing} style={{ whiteSpace: 'nowrap' }}>
                {refreshing ? 'Running…' : '⟳ Run Now'}
              </button>
            </div>
          </div>
        ) : (
          <div className="grid-2">
            {insights.combos.map((combo) => (
              <div key={combo.id} className="card">
                <div className="card-body">
                  <div style={{ fontWeight: 700, marginBottom: 8 }}>
                    {combo.itemNames.join(' + ')}
                    <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 6 }}>
                      (Ordered together {combo.occurrenceCount} times)
                    </span>
                  </div>
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
                    Confidence: <strong>{formatPct(combo.confidence * 100)}</strong>
                  </div>
                  <button
                    className={combo.isPromoted ? 'btn btn-secondary' : 'btn btn-primary'}
                    onClick={() => handlePromoteCombo(combo.id, combo.itemNames.join(' + '))}
                    disabled={combo.isPromoted}
                    style={{ width: '100%' }}
                  >
                    {combo.isPromoted ? 'Added to Menu' : 'Add To Menu'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 style={{ marginBottom: 'var(--space-3)' }}>Added Combos</h2>
        {insights.promotedIds.length === 0 ? (
          <div className="card">
            <div className="card-body">
              Click 'Add To Menu' on at least one combo above to add it to your Live POS Menu under the "Combos" Category.
            </div>
          </div>
        ) : (
          <div className="card">
            <div className="card-body">
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Currently Added Combos:</div>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {insights.combos.filter((c) => c.isPromoted).map((combo) => (
                  <li key={combo.id} style={{ marginBottom: 4 }}>
                    {combo.itemNames.join(' + ')} — Bundle at {formatRupees(combo.bundlePrice)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </section>
    </motion.div>
  )
}

