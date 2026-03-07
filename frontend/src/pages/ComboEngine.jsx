import { useEffect, useMemo, useState, useCallback } from 'react'
import { motion } from 'motion/react'
import { getCombos, getDashboardMetrics, getMenuMatrix, promoteCombo as promoteComboApi } from '../api/client'
import { formatPct, formatRupees } from '../utils/format'
import { buildComboInsights } from '../utils/revenueInsights'
import { useTranslation } from '../context/LanguageContext'

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
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [combosRaw, setCombosRaw] = useState([])
  const [menuItems, setMenuItems] = useState([])
  const [totalOrders, setTotalOrders] = useState(0)
  const [promotedIds, setPromotedIds] = useState([])
  const [error, setError] = useState(null)
  const [mlSummary, setMlSummary] = useState(null)  // From combo API: trained on N orders, pricing model, etc.
  const [activeTab, setActiveTab] = useState('combos')

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
        setMlSummary(comboData?.ml_summary ?? null)
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
  const tabs = [
    { id: 'combos', label: 'Combo Suggestions', icon: '🎯' },
    { id: 'ml', label: 'Combo Insights', icon: '📊' },
  ]

  return (
    <motion.div
      className="app-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="app-hero">
        <div>
          <div className="app-hero-eyebrow">{t('page_combo_eyebrow')}</div>
          <h1 className="app-hero-title">{t('page_combo_title')}</h1>
          <p className="app-hero-sub">{t('page_combo_sub')}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignSelf: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={() => loadCombos(true)}
            disabled={refreshing}
            style={{ whiteSpace: 'nowrap' }}
          >
            {refreshing ? 'Retraining…' : '⟳ Refresh Combos'}
          </button>
        </div>
      </div>

      {/* ML trained on data — summary from combo pipeline (no manual train button) */}
      {mlSummary && (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>ML insights</span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                {mlSummary.trained
                  ? `Trained on ${mlSummary.orders_used ?? 0} orders · ${mlSummary.correlation_pairs ?? 0} correlation pairs · ${mlSummary.combos_saved ?? 0} combos · pricing: ${mlSummary.pricing_model ?? 'rule-based'}`
                  : mlSummary.reason === 'no_transactions'
                    ? 'Place orders to train the combo model automatically.'
                    : 'Model will train automatically when you refresh with order data.'}
              </span>
            </div>
            {mlSummary.window_size != null && (
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Window: last {mlSummary.window_size} orders</span>
            )}
          </div>
        </div>
      )}

      {insights.insufficientData && (
        <div className="card" style={{ marginBottom: 'var(--space-4)', borderColor: 'var(--warning)' }}>
          <div className="card-body" style={{ fontSize: 13 }}>
            Limited order history detected (under 30 records). Combo recommendations will improve as more orders are placed.
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 'var(--space-5)', borderBottom: '1px solid var(--border-dim)', paddingBottom: 0 }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 20px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
              color: activeTab === tab.id ? 'var(--accent)' : 'var(--text-muted)',
              fontWeight: activeTab === tab.id ? 700 : 500,
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB: Combo Suggestions ── */}
      {activeTab === 'combos' && (
        <>
          <section
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
              gap: 'var(--space-3)',
              marginBottom: 'var(--space-5)',
            }}
          >
            <div className="card"><div className="card-body"><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('page_combo_total')}</div><div style={{ fontSize: 28, fontWeight: 800 }}>{summary.totalCombos}</div></div></div>
            <div className="card"><div className="card-body"><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('page_combo_avg_aov')}</div><div style={{ fontSize: 28, fontWeight: 800, color: 'var(--accent)' }}>{formatPct(summary.avgAovUpliftPct)}</div></div></div>
            <div className="card"><div className="card-body"><div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('page_combo_active')}</div><div style={{ fontSize: 28, fontWeight: 800, color: 'var(--success)' }}>{summary.activePromoted}</div></div></div>
          </section>

          <section style={{ marginBottom: 'var(--space-6)' }}>
            <h2 style={{ marginBottom: 'var(--space-3)' }}>{t('page_combo_recommended')}</h2>
            {!hasCombos ? (
              <div className="card">
                <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <span>{t('page_combo_no_data')}</span>
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
                        {combo.isPromoted ? t('page_combo_promoted_btn') : t('page_combo_promote_btn')}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 style={{ marginBottom: 'var(--space-3)' }}>{t('page_combo_promoted')}</h2>
            {insights.promotedIds.length === 0 ? (
              <div className="card">
                <div className="card-body">
                  {t('page_combo_promote_tip')}
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
        </>
      )}

      {/* ── TAB: Combo Insights ── */}
      {activeTab === 'ml' && (
        <>
          <section style={{ marginBottom: 'var(--space-6)' }}>
            <h2 style={{ marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 8 }}>
              📊 Combo insights
            </h2>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 'var(--space-4)' }}>
              Insights are produced automatically from your order data: correlation (Phi/Pearson) finds items ordered together, then bundle pricing uses the trained model or rule-based fallback. No manual training — refresh combos to retrain on latest orders.
            </p>

            {mlSummary?.trained ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 'var(--space-3)', marginBottom: 'var(--space-5)' }}>
                <div className="card"><div className="card-body" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Orders used</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--accent)' }}>{mlSummary.orders_used ?? 0}</div>
                </div></div>
                <div className="card"><div className="card-body" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Correlation pairs</div>
                  <div style={{ fontSize: 22, fontWeight: 800 }}>{mlSummary.correlation_pairs ?? 0}</div>
                </div></div>
                <div className="card"><div className="card-body" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Combos saved</div>
                  <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--success)' }}>{mlSummary.combos_saved ?? 0}</div>
                </div></div>
                <div className="card"><div className="card-body" style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pricing</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: mlSummary.pricing_model === 'ml' ? 'var(--success)' : 'var(--text-secondary)' }}>{mlSummary.pricing_model === 'ml' ? 'ML' : 'Rule-based'}</div>
                </div></div>
              </div>
            ) : (
              <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
                <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--text-muted)' }}>
                  {totalOrders === 0 ? 'No orders yet. Place orders and refresh combos to train the model automatically.' : 'Refresh combos to run the ML pipeline on your latest order data.'}
                </div>
              </div>
            )}

            <h3 style={{ marginBottom: 'var(--space-3)', fontSize: 14, fontWeight: 700 }}>Per-combo metrics (confidence, lift, support)</h3>
            {insights.combos.length === 0 ? (
              <div className="card">
                <div className="card-body" style={{ color: 'var(--text-muted)', fontSize: 13 }}>No combos yet. Refresh combos to generate suggestions from your data.</div>
              </div>
            ) : (
              <div className="card" style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-strong)' }}>
                      <th style={{ textAlign: 'left', padding: '10px 12px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Combo</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Confidence</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Lift (corr)</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Support</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: 'var(--text-muted)', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' }}>Occurrences</th>
                    </tr>
                  </thead>
                  <tbody>
                    {insights.combos.map((combo) => (
                      <tr key={combo.id} style={{ borderBottom: '1px solid var(--border-dim)' }}>
                        <td style={{ padding: '10px 12px', fontWeight: 500 }}>{combo.itemNames.join(' + ')}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{(Number(combo.confidence) * 100).toFixed(1)}%</td>
                        <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>{Number(combo.lift).toFixed(3)}</td>
                        <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{(Number(combo.support) * 100).toFixed(2)}%</td>
                        <td style={{ padding: '10px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{combo.occurrenceCount ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </motion.div>
  )
}
