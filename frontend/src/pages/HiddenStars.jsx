import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHiddenStars, getRisks } from '../api/client'
import { formatPct, formatRupees } from '../utils/format'
import { motion } from 'motion/react'
import { ScrollReveal, StaggerReveal, fadeInUp, staggerItem } from '../utils/animations'

export default function HiddenStars() {
  const navigate = useNavigate()
  const [stars, setStars] = useState([])
  const [risks, setRisks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    Promise.all([
      getHiddenStars(),
      getRisks().catch(() => ({ items: [] })),
    ])
      .then(([hsData, riskData]) => {
        if (!active) return
        setStars(hsData?.items || [])
        setRisks((riskData?.items || []).slice(0, 8))
      })
      .catch((err) => console.error('HiddenStars load failed:', err))
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  if (loading) {
    return (
      <div className="app-page">
        <div className="skeleton" style={{ height: 84, marginBottom: 'var(--space-5)' }} />
        <div className="grid-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 160 }} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <motion.div
      className="app-page"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div className="app-hero" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <div>
          <div className="app-hero-eyebrow">Intelligence</div>
          <h1 className="app-hero-title">Hidden Stars & Risk Items</h1>
          <p className="app-hero-sub">High-margin items with low visibility that could become stars with the right promotion, and underperformers that need attention.</p>
        </div>
      </motion.div>

      {/* Summary cards */}
      <div className="grid-2" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card">
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)' }}>
            <div style={{ fontSize: 40, fontWeight: 800, color: 'var(--success)' }}>{stars.length}</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Hidden Stars Found</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                High margin, low visibility — ready to promote
              </div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)' }}>
            <div style={{ fontSize: 40, fontWeight: 800, color: 'var(--danger)' }}>{risks.length}</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Underperformers</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                Low margin, high volume — review pricing or recipe
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Hidden Stars cards */}
      <section style={{ marginBottom: 'var(--space-6)' }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 'var(--space-4)' }}>Hidden Stars — Promotion Opportunities</h2>
        {stars.length === 0 ? (
          <div className="card">
            <div className="card-body" style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              No hidden stars detected. All high-margin items are already visible to your customers.
            </div>
          </div>
        ) : (
          <StaggerReveal className="hs-grid">
            {stars.map((item) => (
              <motion.div key={item.item_id} className="card hs-card" variants={staggerItem}>
                <div className="card-body">
                  <div className="hs-card-top">
                    <div>
                      <div className="hs-card-name">{item.name}</div>
                      <div className="hs-card-category">{item.category}</div>
                    </div>
                    <div className="hs-opp-badge">{item.opportunity_score}</div>
                  </div>

                  <div className="hs-card-stats">
                    <div>
                      <div className="hs-stat-label">CM%</div>
                      <div className="hs-stat-value" style={{ color: 'var(--success)' }}>{formatPct(item.margin_pct)}</div>
                    </div>
                    <div>
                      <div className="hs-stat-label">Popularity</div>
                      <div className="hs-stat-value" style={{ color: 'var(--warning)' }}>{(item.popularity_score * 100).toFixed(0)}/100</div>
                    </div>
                    <div>
                      <div className="hs-stat-label">Price</div>
                      <div className="hs-stat-value">{formatRupees(item.selling_price)}</div>
                    </div>
                  </div>
                  {(item.ml_confidence != null || item.ml_tier) && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                      {item.ml_confidence != null && (
                        <span style={{ fontSize: 10, background: 'color-mix(in srgb, var(--info) 18%, transparent)', color: 'var(--info)', padding: '2px 8px', borderRadius: 'var(--radius-full)', fontWeight: 600 }}>
                          ML {(item.ml_confidence * 100).toFixed(0)}% conf
                        </span>
                      )}
                      {item.ml_tier && (
                        <span style={{ fontSize: 10, textTransform: 'capitalize', color: 'var(--text-secondary)' }}>{item.ml_tier.replace(/_/g, ' ')}</span>
                      )}
                      {item.ml_velocity_trend_pct != null && (
                        <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: item.ml_velocity_trend_pct > 0 ? 'var(--success)' : 'var(--text-muted)' }}>
                          {item.ml_velocity_trend_pct > 0 ? '+' : ''}{item.ml_velocity_trend_pct}% 7d
                        </span>
                      )}
                    </div>
                  )}

                  {item.suggestions && item.suggestions.length > 0 && (
                    <div className="hs-suggestions">
                      <div className="hs-suggestions-title">Suggestions</div>
                      <ul>
                        {item.suggestions.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <button
                    className="btn btn-ghost"
                    style={{ fontSize: 11, marginTop: 8 }}
                    onClick={() => navigate(`/dashboard/menu-analysis?item=${item.item_id}`)}
                  >
                    View in Matrix
                  </button>
                </div>
              </motion.div>
            ))}
          </StaggerReveal>
        )}
      </section>

      {/* Underperformers table */}
      <ScrollReveal variants={fadeInUp}>
        <section className="card">
          <div className="card-header">Underperformers — Need Attention</div>
          <div className="card-body" style={{ padding: 0 }}>
            {risks.length === 0 ? (
              <div style={{ padding: 'var(--space-5)', color: 'var(--text-muted)', fontSize: 13 }}>No underperforming items at the moment.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Item</th>
                    <th>Category</th>
                    <th style={{ textAlign: 'right' }}>Price</th>
                    <th style={{ textAlign: 'right' }}>CM%</th>
                    <th style={{ textAlign: 'right' }}>Popularity</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {risks.map((item) => (
                    <tr key={item.item_id}>
                      <td style={{ fontWeight: 600 }}>{item.name}</td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{item.category}</td>
                      <td className="col-number" style={{ fontWeight: 600 }}>{formatRupees(item.selling_price)}</td>
                      <td className="col-number" style={{ color: 'var(--danger)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                        {formatPct(item.margin_pct || item.cm_percent)}
                      </td>
                      <td className="col-number" style={{ fontFamily: 'var(--font-mono)' }}>
                        {((item.popularity_score || 0) * 100).toFixed(0)}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 200 }}>
                        {item.action || item.risk_reason || 'Review pricing or recipe cost'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </ScrollReveal>
    </motion.div>
  )
}
