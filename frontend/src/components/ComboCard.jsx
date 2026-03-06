import { motion, useInView } from 'motion/react'
import { useRef } from 'react'
import { formatRupees, formatConfidence, formatSupport, formatLift } from '../utils/format'
import { useThresholds } from '../context/SettingsContext'

export default function ComboCard({ combo }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })
  const itemNames = combo.item_names || []
  const thresholds = useThresholds()

  const confPct = (combo.confidence * 100)
  const confColor = confPct >= thresholds.confidence_green_min ? 'var(--success)' : confPct >= thresholds.confidence_yellow_min ? 'var(--warning)' : 'var(--danger)'

  return (
    <motion.div
      ref={ref}
      className="card"
      whileHover={{ y: -4, borderColor: 'var(--border-mid)', boxShadow: 'var(--shadow-lg)', transition: { duration: 0.2 } }}
    >
      <div className="card-header" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {/* Item chips row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {combo.antecedent_name ? (
            <>
              <span style={{
                padding: '3px 10px', borderRadius: 'var(--radius-full)', fontSize: 12, fontWeight: 500,
                background: 'var(--bg-overlay)', color: 'var(--text-primary)',
              }}>{combo.antecedent_name}</span>
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>+</span>
              <span style={{
                padding: '3px 10px', borderRadius: 'var(--radius-full)', fontSize: 12, fontWeight: 500,
                background: 'var(--bg-overlay)', color: 'var(--text-primary)',
              }}>{combo.consequent_name}</span>
            </>
          ) : itemNames.length > 0 ? (
            itemNames.map((name, i) => (
              <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {i > 0 && <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>+</span>}
                <span style={{
                  padding: '3px 10px', borderRadius: 'var(--radius-full)', fontSize: 12, fontWeight: 500,
                  background: 'var(--bg-overlay)', color: 'var(--text-primary)',
                }}>{name}</span>
              </span>
            ))
          ) : (
            <span style={{ fontWeight: 600, fontSize: 13 }}>{combo.name}</span>
          )}
        </div>

        {/* Tags row */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span className="tag tag-star" style={{ fontSize: 10 }}>{formatLift(combo.lift)} lift</span>
          {combo.combo_structure && (
            <span className={`tag tag-${combo.combo_structure === 'diverse' ? 'green' : 'amber'}`} style={{ fontSize: 10 }}>
              {combo.combo_structure === 'diverse' ? 'Cross-category' : 'Same category'}
            </span>
          )}
        </div>
      </div>

      <div className="card-body">
        {/* Confidence bar */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
            <span style={{ color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Confidence</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: confColor }}>{formatConfidence(combo.confidence)}</span>
          </div>
          <div style={{ width: '100%', height: 4, background: 'var(--bg-overlay)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
            <motion.div
              style={{ height: '100%', background: confColor, borderRadius: 'var(--radius-full)' }}
              initial={{ width: 0 }}
              animate={isInView ? { width: `${confPct}%` } : {}}
              transition={{ duration: 0.8, delay: 0.2, ease: [0.25, 0.46, 0.45, 0.94] }}
            />
          </div>
        </div>

        {/* Compact stat row */}
        <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12 }}>
          {combo.support !== undefined && <span>{formatSupport(combo.support)}</span>}
        </div>

        {/* Pricing block */}
        <div style={{ padding: 'var(--space-3) var(--space-4)', background: 'var(--bg-overlay)', borderRadius: 'var(--radius-sm)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
            <span style={{ color: 'var(--text-muted)' }}>Bundle Price</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {combo.sum_original_price && (
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)', textDecoration: 'line-through' }}>
                  ₹{parseFloat(combo.sum_original_price).toFixed(0)}
                </span>
              )}
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)' }}>
                ₹{(parseFloat(combo.suggested_bundle_price) || 0).toFixed(0)}
              </span>
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
            <span style={{ color: 'var(--text-muted)' }}>CM Gain</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--success)' }}>+₹{(parseFloat(combo.cm_gain) || 0).toFixed(0)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
            <span style={{ color: 'var(--text-muted)' }}>Discount</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--warning)' }}>{combo.discount_pct?.toFixed(1)}%</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
