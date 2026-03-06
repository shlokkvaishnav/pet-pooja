import { useState, useRef } from 'react'
import { submitTextOrder, transcribeAudio, confirmOrder } from '../api/client'
import VoiceRecorder from '../components/VoiceRecorder'
import OrderSummary from '../components/OrderSummary'
import KOTTicket from '../components/KOTTicket'
import { motion, AnimatePresence } from 'motion/react'
import { StaggerReveal, staggerContainer, staggerItem } from '../utils/animations'

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).slice(2, 10)
}

export default function VoiceOrder() {
  const [result, setResult] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const sessionId = useRef(generateSessionId())

  const handleTextOrder = async () => {
    if (!textInput.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await submitTextOrder(textInput, sessionId.current)
      setResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Order processing failed')
    }
    setLoading(false)
  }

  const handleAudioRecorded = async (audioBlob) => {
    setLoading(true)
    setError(null)
    try {
      const data = await transcribeAudio(audioBlob, sessionId.current)
      setResult(data)
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail || 'Voice processing failed'
      if (status === 503) setError('Speech recognition is unavailable. Please try text input.')
      else if (status === 422) setError('Could not understand the order. Please try again.')
      else setError(detail)
    }
    setLoading(false)
  }

  const handleConfirm = async () => {
    if (!result?.order) return
    setLoading(true)
    setError(null)
    try {
      await confirmOrder(result.order, result.kot)
      setResult(prev => ({ ...prev, confirmed: true }))
    } catch (err) {
      setError(err.response?.data?.detail || 'Order confirmation failed')
    }
    setLoading(false)
  }

  const handleNewOrder = () => {
    setResult(null)
    setError(null)
    setTextInput('')
    sessionId.current = generateSessionId()
  }

  const confColor = (c) => c >= 0.9 ? 'var(--success)' : c >= 0.85 ? 'var(--warning)' : 'var(--danger)'

  // Determine step: 1=Listen, 2=Review, 3=Confirmed
  const step = result?.confirmed ? 3 : result ? 2 : 1

  return (
    <motion.div
      className="app-page"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <motion.div
        className="app-hero"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div>
          <div className="app-hero-eyebrow">Operations</div>
          <h1 className="app-hero-title">Voice Ordering</h1>
          <p className="app-hero-sub">Live voice-to-order pipeline with multi-turn context.</p>
        </div>
      </motion.div>
      <motion.div
        className="page-header"
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 style={{ fontFamily: 'var(--font-display)' }}>Voice Order</h1>
        <p>Speak or type an order in English, Hindi, or Hinglish</p>
      </motion.div>

      {/* Step indicator */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-6)',
      }}>
        {['Listen', 'Review', 'Confirm'].map((label, i) => {
          const stepNum = i + 1
          const active = step >= stepNum
          return (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              {i > 0 && <div style={{ width: 32, height: 1, background: active ? 'var(--accent)' : 'var(--border-subtle)' }} />}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '4px 12px', borderRadius: 'var(--radius-full)',
                background: active ? 'color-mix(in srgb, var(--accent) 12%, transparent)' : 'var(--bg-surface)',
                border: `1px solid ${active ? 'var(--accent)' : 'var(--border-subtle)'}`,
              }}>
                <span style={{
                  width: 18, height: 18, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
                  background: active ? 'var(--accent)' : 'var(--bg-overlay)',
                  color: active ? 'white' : 'var(--text-muted)',
                }}>{step > stepNum ? '✓' : stepNum}</span>
                <span style={{ fontSize: 12, fontWeight: 500, color: active ? 'var(--text-primary)' : 'var(--text-muted)' }}>{label}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Step 1: Input */}
      {step === 1 && (
        <StaggerReveal className="grid-2" style={{ marginBottom: 24 }} variants={staggerContainer}>
          <motion.div className="card" variants={staggerItem}>
            <div className="card-header">Voice Input</div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 32 }}>
              <VoiceRecorder onRecorded={handleAudioRecorded} />
            </div>
          </motion.div>

          <motion.div className="card" variants={staggerItem}>
            <div className="card-header">Text Input</div>
            <div className="card-body">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="e.g. ek paneer tikka aur do butter naan, extra spicy"
                style={{
                  width: '100%', height: 80, padding: 12,
                  background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)', color: 'var(--text-primary)',
                  fontFamily: 'var(--font-body)', fontSize: 13, resize: 'vertical',
                }}
              />
              <button
                className="btn btn-primary"
                onClick={handleTextOrder}
                disabled={loading || !textInput.trim()}
                style={{ marginTop: 12, width: '100%' }}
              >
                {loading ? 'Processing…' : 'Process Order'}
              </button>
            </div>
          </motion.div>
        </StaggerReveal>
      )}

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            className="error-bar"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
          >
            <span>{error}</span>
            <button onClick={() => setError(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, marginLeft: 'auto' }}>×</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Step 2: Review */}
      <AnimatePresence>
        {result && !result.confirmed && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            {/* Parsed info */}
            <motion.div
              className="card" style={{ marginBottom: 16 }}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.4 }}
            >
              <div className="card-header">Parsed Input</div>
              <div className="card-body">
                {result.transcript && (
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Transcript</span>
                    <p style={{ fontSize: 13, margin: '4px 0 0', padding: 'var(--space-2) var(--space-3)', background: 'var(--bg-overlay)', borderRadius: 'var(--radius-sm)' }}>
                      {result.transcript}
                    </p>
                  </div>
                )}
                {result.normalized && (
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Normalized</span>
                    <p style={{ fontSize: 13, margin: '4px 0 0' }}>{result.normalized}</p>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  {result.intent && <span className={`tag tag-${result.intent === 'ORDER' ? 'star' : 'puzzle'}`}>{result.intent}</span>}
                  {result.detected_language && <span className="tag" style={{ background: 'var(--bg-overlay)', color: 'var(--text-secondary)' }}>{result.detected_language}</span>}
                  {result.session_id && result.turn_count > 1 && (
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>Turn {result.turn_count}</span>
                  )}
                </div>
              </div>
            </motion.div>

            {/* Matched Items */}
            {result.items?.length > 0 && (
              <motion.div
                className="card" style={{ marginBottom: 16 }}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2, duration: 0.4 }}
              >
                <div className="card-header">Matched Items</div>
                <div className="card-body" style={{ padding: 0 }}>
                  <table className="data-table">
                    <thead>
                      <tr><th>Item</th><th style={{ textAlign: 'right' }}>Confidence</th><th style={{ textAlign: 'right' }}>Total</th></tr>
                    </thead>
                    <tbody>
                      {result.items.map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 600, fontSize: 13 }}>
                            {item.quantity}× {item.item_name}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <span style={{
                              fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 600,
                              padding: '2px 8px', borderRadius: 'var(--radius-full)',
                              background: `color-mix(in srgb, ${confColor(item.confidence)} 15%, transparent)`,
                              color: confColor(item.confidence),
                            }}>
                              {Math.round(item.confidence * 100)}%
                            </span>
                          </td>
                          <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹{item.line_total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}

            {/* Disambiguation */}
            {result.needs_clarification && result.disambiguation?.length > 0 && (
              <motion.div
                className="card" style={{ marginBottom: 16, borderColor: 'var(--warning)' }}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3, duration: 0.4 }}
              >
                <div className="card-header" style={{ color: 'var(--warning)' }}>Did you mean…?</div>
                <div className="card-body">
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                    Some items had low match confidence. Please verify:
                  </p>
                  {result.disambiguation.map((d, idx) => (
                    <div key={idx} style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                        Matched: "{d.item_name}" <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: confColor(d.confidence) }}>({Math.round(d.confidence * 100)}%)</span>
                      </div>
                      {d.alternatives?.length > 0 && (
                        <div style={{ paddingLeft: 12 }}>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Alternatives: </span>
                          {d.alternatives.map((alt, ai) => (
                            <span key={ai} style={{ fontSize: 12, marginRight: 12, fontFamily: 'var(--font-mono)' }}>
                              {alt.item_name} ({Math.round(alt.confidence * 100)}%)
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* No Items Warning */}
            {result.needs_clarification && (!result.disambiguation || result.disambiguation.length === 0) && (
              <motion.div
                className="card" style={{ marginBottom: 16, borderColor: 'var(--warning)' }}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <div className="card-body">
                  <p style={{ color: 'var(--warning)', fontSize: 13 }}>No menu items were recognized. Please try rephrasing.</p>
                </div>
              </motion.div>
            )}

            {/* Session Cart */}
            {result.session_items?.length > result.items?.length && (
              <motion.div
                className="card" style={{ marginBottom: 16 }}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, duration: 0.4 }}
              >
                <div className="card-header">Full Cart (all turns)</div>
                <div className="card-body">
                  {result.session_items.map((item, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 13 }}>
                      <span>{item.quantity}× {item.item_name}</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹{item.line_total}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Order + KOT side by side */}
            <StaggerReveal className="grid-2" variants={staggerContainer}>
              {result.order && <motion.div variants={staggerItem}><OrderSummary order={result.order} /></motion.div>}
              {result.kot && <motion.div variants={staggerItem}><KOTTicket kot={result.kot} /></motion.div>}
            </StaggerReveal>

            {/* Upsell */}
            {result.upsell_suggestions?.length > 0 && (
              <motion.div
                className="card" style={{ marginTop: 16 }}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.4 }}
              >
                <div className="card-header">Suggested Add-ons</div>
                <div className="card-body">
                  {result.upsell_suggestions.map((u, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{u.name || u.suggestion_text}</span>
                      {u.reason && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>- {u.reason}</span>}
                      {u.selling_price && <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600, marginLeft: 'auto' }}>₹{u.selling_price}</span>}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Action Buttons */}
            {result.order && (
              <motion.div
                style={{ marginTop: 16, display: 'flex', gap: 12 }}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 0.4 }}
              >
                <motion.button
                  className="btn btn-primary"
                  onClick={handleConfirm}
                  disabled={loading || result.needs_clarification}
                  style={{ flex: 1 }}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {loading ? 'Confirming…' : 'Confirm Order'}
                </motion.button>
                <motion.button
                  className="btn btn-ghost"
                  onClick={handleNewOrder}
                  style={{ flex: 1 }}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  New Order
                </motion.button>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Step 3: Confirmed */}
      <AnimatePresence>
        {result?.confirmed && (
          <motion.div
            className="card" style={{ marginTop: 16, borderColor: 'var(--success)' }}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
          >
            <div className="card-body" style={{ textAlign: 'center', padding: 32 }}>
              <motion.div
                style={{ fontSize: 48, marginBottom: 8 }}
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.2, 1] }}
                transition={{ duration: 0.5 }}
              >
                ✓
              </motion.div>
              <p style={{ fontSize: 18, fontFamily: 'var(--font-display)', fontWeight: 900, color: 'var(--success)', marginBottom: 4 }}>
                Order Confirmed
              </p>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>KOT has been sent to the kitchen</p>
              <motion.button
                className="btn btn-primary"
                onClick={handleNewOrder}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Start New Order
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
