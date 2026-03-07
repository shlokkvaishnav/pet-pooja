import { useEffect, useMemo, useState, useCallback } from 'react'
import { motion } from 'motion/react'
import { getCombos, getDashboardMetrics, getMenuMatrix, promoteCombo as promoteComboApi, trainMLPipeline, getMLStatus, getMLAov, getMLDemand } from '../api/client'
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

/* ── ML Pipeline Status Badge ── */
function PipelineStatusBadge({ status }) {
  if (!status || status === 'never_run') {
    return <span className="tag" style={{ background: 'var(--bg-overlay)', color: 'var(--text-muted)' }}>Not Trained</span>
  }
  const colors = {
    completed: { bg: 'rgba(52,211,153,0.15)', color: 'var(--success)' },
    partial: { bg: 'rgba(251,191,36,0.15)', color: 'var(--warning)' },
    running: { bg: 'rgba(96,165,250,0.15)', color: 'var(--accent)' },
    failed: { bg: 'rgba(248,113,113,0.15)', color: 'var(--danger)' },
  }
  const style = colors[status] || colors.partial
  return <span className="tag" style={{ background: style.bg, color: style.color, fontWeight: 600 }}>{status}</span>
}

/* ── Staleness indicator ── */
function StalenessTag({ staleness }) {
  if (!staleness) return null
  const styles = {
    fresh: { bg: 'rgba(52,211,153,0.12)', color: 'var(--success)', label: '● Fresh' },
    aging: { bg: 'rgba(251,191,36,0.12)', color: 'var(--warning)', label: '● Aging' },
    stale: { bg: 'rgba(248,113,113,0.12)', color: 'var(--danger)', label: '● Stale' },
  }
  const s = styles[staleness] || styles.stale
  return <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 'var(--radius-full)', background: s.bg, color: s.color, fontWeight: 600 }}>{s.label}</span>
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

  // ML pipeline state
  const [mlStatus, setMlStatus] = useState(null)
  const [aovData, setAovData] = useState(null)
  const [demandData, setDemandData] = useState(null)
  const [mlTraining, setMlTraining] = useState(false)
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

  const loadMLData = useCallback(() => {
    Promise.allSettled([
      getMLStatus(),
      getMLAov(),
      getMLDemand(7),
    ]).then(([statusRes, aovRes, demandRes]) => {
      if (statusRes.status === 'fulfilled') setMlStatus(statusRes.value)
      if (aovRes.status === 'fulfilled') setAovData(aovRes.value)
      if (demandRes.status === 'fulfilled') setDemandData(demandRes.value)
    })
  }, [])

  useEffect(() => {
    loadCombos()
    loadMLData()
  }, [loadCombos, loadMLData])

  const handleTrainPipeline = async () => {
    setMlTraining(true)
    try {
      await trainMLPipeline()
      loadMLData()
      loadCombos(true)
    } catch (err) {
      console.error('ML training failed:', err)
    } finally {
      setMlTraining(false)
    }
  }

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
  const pipelineRun = mlStatus?.last_run
  const tabs = [
    { id: 'combos', label: 'Combo Suggestions', icon: '🎯' },
    { id: 'ml', label: 'ML Intelligence', icon: '🧠' },
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
          <button
            className="btn btn-primary"
            onClick={handleTrainPipeline}
            disabled={mlTraining}
            style={{ whiteSpace: 'nowrap' }}
          >
            {mlTraining ? '⏳ Training ML…' : '🧠 Train ML Pipeline'}
          </button>
        </div>
      </div>

      {/* ML Pipeline Status Bar */}
      {mlStatus && (
        <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>ML Pipeline</span>
              <PipelineStatusBadge status={mlStatus.status} />
              <StalenessTag staleness={mlStatus.staleness} />
            </div>
            {pipelineRun && (
              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                <span>Orders: <strong style={{ color: 'var(--text-primary)' }}>{pipelineRun.orders_used || 0}</strong></span>
                <span>Duration: <strong style={{ color: 'var(--text-primary)' }}>{pipelineRun.training_duration_sec?.toFixed(1)}s</strong></span>
                {pipelineRun.age_hours != null && (
                  <span>Age: <strong style={{ color: 'var(--text-primary)' }}>{pipelineRun.age_hours < 1 ? '<1h' : `${pipelineRun.age_hours.toFixed(0)}h`}</strong></span>
                )}
              </div>
            )}
            {mlStatus.recommendation && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>{mlStatus.recommendation}</div>
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

      {/* ── TAB: ML Intelligence ── */}
      {activeTab === 'ml' && (
        <>
          {/* AOV Insights */}
          <section style={{ marginBottom: 'var(--space-6)' }}>
            <h2 style={{ marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 8 }}>
              📊 AOV Insights
              {aovData?.model_metrics && (
                <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)' }}>
                  Model R² = {aovData.model_metrics.cv_r2}
                </span>
              )}
            </h2>

            {!aovData || aovData.current_aov === undefined ? (
              <div className="card">
                <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--text-muted)' }}>
                  No AOV data available. Click <strong>Train ML Pipeline</strong> to generate predictions.
                </div>
              </div>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                  <div className="card"><div className="card-body">
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Current AOV</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--accent)' }}>{formatRupees(aovData.current_aov)}</div>
                  </div></div>
                  <div className="card"><div className="card-body">
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Orders (30d)</div>
                    <div style={{ fontSize: 24, fontWeight: 800 }}>{aovData.total_orders_30d}</div>
                  </div></div>
                  <div className="card"><div className="card-body">
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Min Order</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-secondary)' }}>{formatRupees(aovData.min_order_value)}</div>
                  </div></div>
                  <div className="card"><div className="card-body">
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Max Order</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--success)' }}>{formatRupees(aovData.max_order_value)}</div>
                  </div></div>
                </div>

                {/* AOV by Hour */}
                {aovData.aov_by_hour?.length > 0 && (
                  <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
                    <div className="card-header"><span style={{ fontWeight: 600 }}>AOV by Hour</span></div>
                    <div className="card-body" style={{ overflowX: 'auto' }}>
                      <div style={{ display: 'flex', gap: 0, alignItems: 'flex-end', height: 120, minWidth: aovData.aov_by_hour.length * 40 }}>
                        {aovData.aov_by_hour.map((h) => {
                          const maxAov = Math.max(...aovData.aov_by_hour.map(x => x.actual_aov))
                          const barHeight = maxAov > 0 ? (h.actual_aov / maxAov * 100) : 0
                          return (
                            <div key={h.hour} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                              <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-primary)' }}>{formatRupees(h.actual_aov)}</span>
                              <div style={{
                                width: '60%', height: `${barHeight}%`, minHeight: 4,
                                background: 'linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 60%, transparent))',
                                borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
                                transition: 'height 0.3s',
                              }} />
                              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{h.label}</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {/* AOV by Order Type */}
                {aovData.aov_by_order_type?.length > 0 && (
                  <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
                    <div className="card-header"><span style={{ fontWeight: 600 }}>AOV by Order Type</span></div>
                    <div className="card-body">
                      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(aovData.aov_by_order_type.length, 4)}, 1fr)`, gap: 'var(--space-3)' }}>
                        {aovData.aov_by_order_type.map((ot) => (
                          <div key={ot.type} style={{ textAlign: 'center', padding: 'var(--space-3)', background: 'var(--bg-overlay)', borderRadius: 'var(--radius-sm)' }}>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'capitalize', marginBottom: 4 }}>{ot.type.replace(/_/g, ' ')}</div>
                            <div style={{ fontSize: 20, fontWeight: 700 }}>{formatRupees(ot.aov)}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{ot.order_count} orders</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Improvement Opportunities */}
                {aovData.improvement_opportunities?.length > 0 && (
                  <div className="card">
                    <div className="card-header"><span style={{ fontWeight: 600 }}>💡 Improvement Opportunities</span></div>
                    <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {aovData.improvement_opportunities.map((opp, idx) => (
                        <div key={idx} style={{ padding: 'var(--space-3)', background: 'var(--bg-overlay)', borderRadius: 'var(--radius-sm)', borderLeft: '3px solid var(--accent)' }}>
                          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{opp.title}</div>
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{opp.description}</div>
                          <div style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, marginTop: 4 }}>Potential lift: +{opp.potential_lift_pct}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </section>

          {/* Demand Forecasts */}
          <section style={{ marginBottom: 'var(--space-6)' }}>
            <h2 style={{ marginBottom: 'var(--space-3)', display: 'flex', alignItems: 'center', gap: 8 }}>
              📈 Demand Forecasts (7-day)
              {demandData?.model_metrics && (
                <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)' }}>
                  Model R² = {demandData.model_metrics.cv_r2}
                </span>
              )}
            </h2>

            {!demandData?.forecasts?.length && !demandData?.rising_items?.length ? (
              <div className="card">
                <div className="card-body" style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--text-muted)' }}>
                  No demand data available. Click <strong>Train ML Pipeline</strong> to generate forecasts.
                </div>
              </div>
            ) : (
              <>
                {/* Rising / Falling items */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
                  <div className="card">
                    <div className="card-header"><span style={{ fontWeight: 600, color: 'var(--success)' }}>🔥 Rising Items</span></div>
                    <div className="card-body">
                      {(demandData?.rising_items || []).length === 0 ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No rising items detected</div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {(demandData?.rising_items || []).slice(0, 5).map((item) => (
                            <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
                              <span>{item.item_name}</span>
                              <span style={{ color: 'var(--success)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>+{item.trend_pct?.toFixed(0)}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-header"><span style={{ fontWeight: 600, color: 'var(--danger)' }}>📉 Falling Items</span></div>
                    <div className="card-body">
                      {(demandData?.falling_items || []).length === 0 ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No falling items detected</div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {(demandData?.falling_items || []).slice(0, 5).map((item) => (
                            <div key={item.item_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13 }}>
                              <span>{item.item_name}</span>
                              <span style={{ color: 'var(--danger)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{item.trend_pct?.toFixed(0)}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Top Items Forecast Table */}
                {demandData?.forecasts?.length > 0 && (
                  <div className="card">
                    <div className="card-header"><span style={{ fontWeight: 600 }}>Top Items — Predicted Demand</span></div>
                    <div className="card-body" style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                            <th style={{ textAlign: 'left', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>Item</th>
                            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>Last 7d Avg</th>
                            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>Predicted/day</th>
                            <th style={{ textAlign: 'right', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>7d Total</th>
                            <th style={{ textAlign: 'center', padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase' }}>Trend</th>
                          </tr>
                        </thead>
                        <tbody>
                          {demandData.forecasts.slice(0, 15).map((item) => {
                            const trendColor = item.trend === 'rising' ? 'var(--success)' : item.trend === 'falling' ? 'var(--danger)' : 'var(--text-muted)'
                            const trendIcon = item.trend === 'rising' ? '↑' : item.trend === 'falling' ? '↓' : '→'
                            return (
                              <tr key={item.item_id} style={{ borderBottom: '1px solid var(--border-dim)' }}>
                                <td style={{ padding: '8px 12px', fontWeight: 500 }}>{item.item_name}</td>
                                <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{item.last_7d_avg}</td>
                                <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{item.predicted_daily_qty}</td>
                                <td style={{ padding: '8px 12px', textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{item.predicted_total_qty}</td>
                                <td style={{ padding: '8px 12px', textAlign: 'center', color: trendColor, fontWeight: 600 }}>{trendIcon} {item.trend_pct?.toFixed(0)}%</td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Stockout Risks */}
                {demandData?.stockout_risks?.length > 0 && (
                  <div className="card" style={{ marginTop: 'var(--space-4)', borderColor: 'var(--danger)' }}>
                    <div className="card-header"><span style={{ fontWeight: 600, color: 'var(--danger)' }}>⚠️ Stockout Risks</span></div>
                    <div className="card-body">
                      {demandData.stockout_risks.map((risk) => (
                        <div key={risk.item_id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-dim)', fontSize: 13 }}>
                          <span>{risk.item_name}</span>
                          <span style={{ color: risk.urgency === 'critical' ? 'var(--danger)' : 'var(--warning)', fontWeight: 600 }}>
                            {risk.days_until_stockout} days left ({risk.urgency})
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </section>

          {/* Model Performance */}
          {pipelineRun?.model_metrics && (
            <section>
              <h2 style={{ marginBottom: 'var(--space-3)' }}>🔬 Model Performance</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 'var(--space-3)' }}>
                {Object.entries(pipelineRun.model_metrics).map(([model, metrics]) => {
                  const status = metrics?.status || 'unknown'
                  const statusColors = {
                    completed: 'var(--success)', skipped: 'var(--warning)', failed: 'var(--danger)',
                  }
                  return (
                    <div key={model} className="card">
                      <div className="card-body">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <span style={{ fontWeight: 700, fontSize: 13, textTransform: 'capitalize' }}>{model}</span>
                          <span style={{ fontSize: 10, fontWeight: 600, color: statusColors[status] || 'var(--text-muted)' }}>{status}</span>
                        </div>
                        {metrics?.cv_r2 !== undefined && (
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                            R² = <strong>{metrics.cv_r2}</strong>
                          </div>
                        )}
                        {metrics?.mae !== undefined && (
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                            MAE = <strong>{metrics.mae}</strong>
                          </div>
                        )}
                        {metrics?.training_samples !== undefined && (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                            {metrics.training_samples} samples
                          </div>
                        )}
                        {metrics?.training_baskets !== undefined && (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                            {metrics.training_baskets} baskets
                          </div>
                        )}
                        {metrics?.total_baskets !== undefined && (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                            {metrics.total_baskets} baskets
                          </div>
                        )}
                        {metrics?.reason && (
                          <div style={{ fontSize: 11, color: 'var(--warning)', marginTop: 4 }}>
                            {metrics.reason.replace(/_/g, ' ')}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </section>
          )}
        </>
      )}
    </motion.div>
  )
}
