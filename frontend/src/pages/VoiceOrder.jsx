import { useState, useRef, useCallback } from 'react'
import { submitTextOrder, transcribeAudio, confirmOrder } from '../api/client'
import VoiceRecorder from '../components/VoiceRecorder'
import OrderSummary from '../components/OrderSummary'
import KOTTicket from '../components/KOTTicket'
import { motion, AnimatePresence } from 'motion/react'
import { StaggerReveal, staggerContainer, staggerItem } from '../utils/animations'
import { Trash2, ShoppingCart, ChevronUp, ChevronDown, X } from 'lucide-react'

function generateSessionId() {
  return 'sess-' + Math.random().toString(36).slice(2, 10)
}

export default function VoiceOrder() {
  const [result, setResult] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [actionFeedback, setActionFeedback] = useState(null) // {type, message}
  const [orderTabOpen, setOrderTabOpen] = useState(false)
  const sessionId = useRef(generateSessionId())
  const currentAudioRef = useRef(null)

  // ── TTS Audio Playback ──
  const playTTSAudio = useCallback((base64Audio) => {
    if (!base64Audio) return

    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current.src = ''
    }

    const bytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0))
    const blob = new Blob([bytes], { type: 'audio/mp3' })
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    currentAudioRef.current = audio

    audio.onended = () => {
      URL.revokeObjectURL(url)
      setIsSpeaking(false)
    }
    audio.onerror = () => {
      URL.revokeObjectURL(url)
      setIsSpeaking(false)
    }
    setIsSpeaking(true)
    audio.play().catch(() => setIsSpeaking(false))
  }, [])

  // ── Stop TTS when user starts recording ──
  const handleInterruptAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current.src = ''
      setIsSpeaking(false)
    }
  }, [])

  // ── Process result and show feedback ──
  const processResult = useCallback((data) => {
    setResult(data)

    // Auto-open order tab when items exist in cart
    if (data.session_items?.length > 0) {
      setOrderTabOpen(true)
    } else {
      setOrderTabOpen(false)
    }

    // Show action feedback based on intent
    const intent = data.intent
    if (intent === 'CANCEL') {
      const cancelledNames = data.items?.map(i => i.item_name).join(', ')
      if (cancelledNames) {
        setActionFeedback({ type: 'cancel', message: `Removed: ${cancelledNames}` })
      } else if (!data.session_items?.length) {
        setActionFeedback({ type: 'cancel', message: 'Order cleared' })
      } else {
        setActionFeedback({ type: 'info', message: data.tts_text || data.user_messages?.[0] || 'Which item to remove?' })
      }
    } else if (intent === 'MODIFY') {
      setActionFeedback({ type: 'modify', message: data.tts_text || 'Item updated' })
    } else if (intent === 'ORDER' && data.items?.length > 0) {
      const names = data.items.map(i => `${i.quantity}× ${i.item_name}`).join(', ')
      setActionFeedback({ type: 'add', message: `Added: ${names}` })
    } else if (intent === 'CONFIRM') {
      // Voice-triggered confirmation
      setActionFeedback({ type: 'confirm', message: 'Order confirmed via voice!' })
    } else if (data.user_messages?.length > 0) {
      setActionFeedback({ type: 'info', message: data.user_messages[0] })
    } else {
      setActionFeedback(null)
    }

    // Auto-play TTS response
    if (data.tts_audio_b64) playTTSAudio(data.tts_audio_b64)

    // Auto-confirm if voice said "confirm"
    if (intent === 'CONFIRM' && data.session_items?.length > 0) {
      handleVoiceConfirm(data)
    }
  }, [playTTSAudio])

  const handleTextOrder = async () => {
    if (!textInput.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await submitTextOrder(textInput, sessionId.current)
      processResult(data)
      setTextInput('')
    } catch (err) {
      setError(err.response?.data?.detail || err.detail || 'Order processing failed')
    }
    setLoading(false)
  }

  const handleAudioRecorded = async (audioBlob) => {
    setLoading(true)
    setError(null)
    try {
      const data = await transcribeAudio(audioBlob, sessionId.current)
      processResult(data)
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail || err.detail || 'Voice processing failed'
      if (status === 503) setError('Speech recognition is unavailable. Please try text input.')
      else if (status === 422) setError('Could not understand the order. Please try again.')
      else setError(detail)
    }
    setLoading(false)
  }

  // ── Remove item via UI button ──
  const handleRemoveItem = async (itemName) => {
    setLoading(true)
    setError(null)
    try {
      const data = await submitTextOrder(`remove ${itemName}`, sessionId.current)
      processResult(data)
    } catch (err) {
      setError(err.response?.data?.detail || err.detail || 'Failed to remove item')
    }
    setLoading(false)
  }

  // ── Voice-triggered confirm ──
  const handleVoiceConfirm = async (data) => {
    const orderToConfirm = data.session_order || data.order
    if (!orderToConfirm) return
    setLoading(true)
    try {
      await confirmOrder(orderToConfirm, data.kot)
      setResult(prev => ({ ...prev, confirmed: true }))
    } catch (err) {
      setError(err.response?.data?.detail || err.detail || 'Order confirmation failed')
    }
    setLoading(false)
  }

  const handleConfirm = async () => {
    const orderToConfirm = result?.session_order || result?.order
    if (!orderToConfirm) return
    setLoading(true)
    setError(null)
    try {
      await confirmOrder(orderToConfirm, result.kot)
      setResult(prev => ({ ...prev, confirmed: true }))
    } catch (err) {
      setError(err.response?.data?.detail || err.detail || 'Order confirmation failed')
    }
    setLoading(false)
  }

  const handleNewOrder = () => {
    handleInterruptAudio()
    setResult(null)
    setError(null)
    setTextInput('')
    setActionFeedback(null)
    setOrderTabOpen(false)
    sessionId.current = generateSessionId()
  }

  const confColor = (c) => c >= 0.9 ? 'var(--success)' : c >= 0.85 ? 'var(--warning)' : 'var(--danger)'

  // Cart items from session (accumulated across all turns)
  const cartItems = result?.session_items || []
  const hasCart = cartItems.length > 0

  // Effective order for display (use session_order which covers all turns)
  const effectiveOrder = result?.session_order || result?.order

  // Determine step: 1=Listen, 2=Review (with continued input), 3=Confirmed
  const step = result?.confirmed ? 3 : result ? 2 : 1

  // Feedback colors
  const feedbackStyles = {
    add: { bg: 'color-mix(in srgb, var(--success) 12%, transparent)', color: 'var(--success)', icon: '+' },
    cancel: { bg: 'color-mix(in srgb, var(--danger) 12%, transparent)', color: 'var(--danger)', icon: '−' },
    modify: { bg: 'color-mix(in srgb, var(--warning) 12%, transparent)', color: 'var(--warning)', icon: '↻' },
    confirm: { bg: 'color-mix(in srgb, var(--success) 12%, transparent)', color: 'var(--success)', icon: '✓' },
    info: { bg: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)', icon: 'ℹ' },
  }

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
        <p>Speak or type to order, modify, remove items, or confirm</p>
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

      {/* ── Voice/Text Input — visible in Step 1 AND Step 2 ── */}
      {step <= 2 && !result?.confirmed && (
        <StaggerReveal className="grid-2" style={{ marginBottom: 24 }} variants={staggerContainer}>
          <motion.div className="card" variants={staggerItem}>
            <div className="card-header">
              Voice Input
              {hasCart && <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}> — say "remove", "add", or "confirm"</span>}
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 32 }}>
              <VoiceRecorder onRecorded={handleAudioRecorded} onStartRecording={handleInterruptAudio} />
              {isSpeaking && (
                <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 20, justifyContent: 'center', marginTop: 12 }}>
                  {[8, 16, 10].map((h, i) => (
                    <span key={i} style={{
                      width: 3, height: h, background: 'var(--accent, #ff6b35)', borderRadius: 2,
                      animation: 'speakwave 0.8s ease-in-out infinite',
                      animationDelay: `${i * 0.15}s`,
                    }} />
                  ))}
                  <style>{`@keyframes speakwave { 0%,100%{transform:scaleY(1)} 50%{transform:scaleY(1.8)} }`}</style>
                </div>
              )}
            </div>
          </motion.div>

          <motion.div className="card" variants={staggerItem}>
            <div className="card-header">
              Text Input
              {hasCart && <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}> — "remove paneer tikka", "add 1 coke"</span>}
            </div>
            <div className="card-body">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTextOrder() } }}
                placeholder={hasCart
                  ? 'e.g. remove butter naan, add one lassi, extra spicy dal makhani'
                  : 'e.g. ek paneer tikka aur do butter naan, extra spicy'
                }
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
                {loading ? 'Processing…' : hasCart ? 'Update Order' : 'Process Order'}
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

      {/* ── Action Feedback Banner ── */}
      <AnimatePresence>
        {actionFeedback && step === 2 && (
          <motion.div
            initial={{ opacity: 0, y: -10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            transition={{ duration: 0.3 }}
            style={{
              marginBottom: 16,
              padding: '10px 16px',
              borderRadius: 'var(--radius-sm)',
              background: feedbackStyles[actionFeedback.type]?.bg || 'var(--bg-surface)',
              border: `1px solid ${feedbackStyles[actionFeedback.type]?.color || 'var(--border-subtle)'}`,
              display: 'flex', alignItems: 'center', gap: 10,
            }}
          >
            <span style={{
              width: 22, height: 22, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: feedbackStyles[actionFeedback.type]?.color, color: 'white', fontSize: 12, fontWeight: 700,
            }}>
              {feedbackStyles[actionFeedback.type]?.icon}
            </span>
            <span style={{ fontSize: 13, fontWeight: 500, color: feedbackStyles[actionFeedback.type]?.color }}>
              {actionFeedback.message}
            </span>
            {result?.tts_text && result.tts_text !== actionFeedback.message && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 8, fontStyle: 'italic' }}>
                "{result.tts_text}"
              </span>
            )}
            <button
              onClick={() => setActionFeedback(null)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16, marginLeft: 'auto' }}
            >×</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Step 2: Review — with live cart */}
      <AnimatePresence>
        {result && !result.confirmed && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >            {/* ── Live Cart (from session_items) — shown FIRST ── */}
            {hasCart && (
              <motion.div
                className="card" style={{ marginBottom: 16 }}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.4 }}
              >
                <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ShoppingCart size={14} />
                  <span>Your Cart</span>
                  <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    {cartItems.length} {cartItems.length === 1 ? 'item' : 'items'}
                  </span>
                </div>
                <div className="card-body" style={{ padding: 0 }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th style={{ textAlign: 'right' }}>Price</th>
                        <th style={{ textAlign: 'right' }}>Total</th>
                        <th style={{ textAlign: 'center', width: 50 }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {cartItems.map((item, idx) => (
                        <motion.tr
                          key={item.item_id || idx}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.05 }}
                        >
                          <td style={{ fontWeight: 600, fontSize: 13 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              {item.is_veg !== undefined && (
                                <span className={item.is_veg ? 'veg-indicator veg' : 'veg-indicator non-veg'} />
                              )}
                              <span>{item.quantity}× {item.item_name || item.name}</span>
                            </div>
                            {/* Modifier chips */}
                            {item.modifiers && Object.keys(item.modifiers).some(k => {
                              const v = item.modifiers[k]
                              return v && v !== 'medium' && v !== 'regular' && k !== 'warnings' && (Array.isArray(v) ? v.length > 0 : v)
                            }) && (
                              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 3 }}>
                                {item.modifiers.spice_level && item.modifiers.spice_level !== 'medium' && (
                                  <span style={{
                                    fontSize: 10, padding: '1px 6px', borderRadius: 'var(--radius-full)',
                                    background: 'var(--warning-subtle)', color: 'var(--warning)',
                                  }}>🌶️ {item.modifiers.spice_level}</span>
                                )}
                                {item.modifiers.add_ons?.map((a, i) => (
                                  <span key={i} style={{
                                    fontSize: 10, padding: '1px 6px', borderRadius: 'var(--radius-full)',
                                    background: 'var(--bg-overlay)', color: 'var(--text-secondary)',
                                  }}>+ {a.replace('_', ' ')}</span>
                                ))}
                              </div>
                            )}
                          </td>
                          <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>
                            ₹{item.unit_price}
                          </td>
                          <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>₹{item.line_total}</td>
                          <td style={{ textAlign: 'center' }}>
                            <button
                              onClick={() => handleRemoveItem(item.item_name || item.name)}
                              disabled={loading}
                              style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                color: 'var(--text-muted)', padding: 4, borderRadius: 'var(--radius-sm)',
                                transition: 'color 0.2s',
                              }}
                              onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
                              title={`Remove ${item.item_name || item.name}`}
                            >
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>

                  {/* Cart totals */}
                  {effectiveOrder && (
                    <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-subtle)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                        <span>Subtotal</span>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>₹{effectiveOrder.subtotal}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
                        <span>GST (5%)</span>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>₹{effectiveOrder.tax}</span>
                      </div>
                      <div style={{
                        display: 'flex', justifyContent: 'space-between',
                        fontSize: 16, fontWeight: 800, fontFamily: 'var(--font-mono)',
                        color: 'var(--accent)',
                        borderTop: '1px solid var(--border-mid)', paddingTop: 8,
                      }}>
                        <span style={{ fontFamily: 'var(--font-body)' }}>Total</span>
                        <span>₹{effectiveOrder.total}</span>
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {/* Parsed info (last turn) */}
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
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  {result.intent && (
                    <span className={`tag tag-${
                      result.intent === 'ORDER' ? 'star' :
                      result.intent === 'CANCEL' ? 'puzzle' :
                      result.intent === 'MODIFY' ? 'puzzle' :
                      result.intent === 'CONFIRM' ? 'star' : 'puzzle'
                    }`}>
                      {result.intent}
                    </span>
                  )}
                  {result.detected_language && <span className="tag" style={{ background: 'var(--bg-overlay)', color: 'var(--text-secondary)' }}>{result.detected_language}</span>}
                  {result.session_id && result.turn_count > 1 && (
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>Turn {result.turn_count}</span>
                  )}
                </div>
              </div>
            </motion.div>

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

            {/* No Items Warning — only show if first turn and no cart */}
            {result.needs_clarification && (!result.disambiguation || result.disambiguation.length === 0) && !hasCart && result.intent === 'ORDER' && (
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

            {/* Empty cart after cancel-all */}
            {!hasCart && result.intent === 'CANCEL' && (
              <motion.div
                className="card" style={{ marginBottom: 16 }}
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <div className="card-body" style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
                  <ShoppingCart size={32} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p style={{ fontSize: 13 }}>Cart is empty. Start ordering by speaking or typing above.</p>
                </div>
              </motion.div>
            )}

            {/* Upsell */}
            {result.upsell_suggestions?.length > 0 && hasCart && (
              <motion.div
                className="card" style={{ marginBottom: 16 }}
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
            <motion.div
              style={{ marginTop: 16, display: 'flex', gap: 12 }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.4 }}
            >
              {hasCart && (
                <motion.button
                  className="btn btn-primary"
                  onClick={handleConfirm}
                  disabled={loading || (result.needs_clarification && result.intent === 'ORDER' && cartItems.length === 0)}
                  style={{ flex: 1 }}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {loading ? 'Confirming…' : `Confirm Order (₹${effectiveOrder?.total || 0})`}
                </motion.button>
              )}
              <motion.button
                className="btn btn-ghost"
                onClick={handleNewOrder}
                style={{ flex: hasCart ? 0 : 1, minWidth: hasCart ? 120 : undefined }}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
              >
                {hasCart ? 'Clear & Restart' : 'New Order'}
              </motion.button>
            </motion.div>
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

      {/* ── Floating Order Tab ── */}
      <AnimatePresence>
        {hasCart && !result?.confirmed && (
          <>
            {/* Floating toggle button */}
            <motion.button
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              onClick={() => setOrderTabOpen(prev => !prev)}
              style={{
                position: 'fixed', bottom: 24, right: 24, zIndex: 1000,
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '12px 20px', borderRadius: 'var(--radius-full)',
                background: 'var(--accent)', color: 'white', border: 'none',
                cursor: 'pointer', fontFamily: 'var(--font-body)',
                fontSize: 14, fontWeight: 700,
                boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
              }}
              whileHover={{ scale: 1.05, y: -2 }}
              whileTap={{ scale: 0.95 }}
            >
              <ShoppingCart size={18} />
              <span>{cartItems.length} {cartItems.length === 1 ? 'item' : 'items'}</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>₹{effectiveOrder?.total || 0}</span>
              {orderTabOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}

              {/* Pulse badge on new item */}
              <motion.span
                key={cartItems.length}
                initial={{ scale: 1.5, opacity: 1 }}
                animate={{ scale: 1, opacity: 0 }}
                transition={{ duration: 0.6 }}
                style={{
                  position: 'absolute', inset: 0, borderRadius: 'var(--radius-full)',
                  border: '2px solid var(--accent)', pointerEvents: 'none',
                }}
              />
            </motion.button>

            {/* Slide-up order panel */}
            <AnimatePresence>
              {orderTabOpen && (
                <motion.div
                  initial={{ y: '100%', opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  exit={{ y: '100%', opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  style={{
                    position: 'fixed', bottom: 80, right: 24, zIndex: 999,
                    width: 360, maxHeight: 'calc(100vh - 140px)',
                    background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-lg)',
                    boxShadow: '0 8px 40px rgba(0,0,0,0.35)',
                    display: 'flex', flexDirection: 'column',
                    overflow: 'hidden',
                  }}
                >
                  {/* Panel header */}
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)',
                    background: 'var(--bg-elevated)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <ShoppingCart size={16} style={{ color: 'var(--accent)' }} />
                      <span style={{ fontWeight: 700, fontSize: 14, fontFamily: 'var(--font-display)' }}>Current Order</span>
                    </div>
                    <button
                      onClick={() => setOrderTabOpen(false)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
                    >
                      <X size={16} />
                    </button>
                  </div>

                  {/* Items list */}
                  <div style={{ overflowY: 'auto', flex: 1, padding: '8px 0' }}>
                    {cartItems.map((item, idx) => (
                      <motion.div
                        key={item.item_id || idx}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.04 }}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 10,
                          padding: '10px 16px',
                          borderBottom: idx < cartItems.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                        }}
                      >
                        {/* Veg/Non-veg dot */}
                        {item.is_veg !== undefined && (
                          <span style={{
                            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                            background: item.is_veg ? '#22c55e' : '#ef4444',
                          }} />
                        )}

                        {/* Item info */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {item.quantity}× {item.item_name || item.name}
                          </div>
                          {/* Modifier tags */}
                          {item.modifiers && item.modifiers.spice_level && item.modifiers.spice_level !== 'medium' && (
                            <span style={{
                              fontSize: 10, padding: '1px 5px', borderRadius: 'var(--radius-full)',
                              background: 'var(--warning-subtle)', color: 'var(--warning)',
                            }}>🌶️ {item.modifiers.spice_level}</span>
                          )}
                        </div>

                        {/* Price */}
                        <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', fontWeight: 600, flexShrink: 0 }}>
                          ₹{item.line_total}
                        </span>

                        {/* Remove btn */}
                        <button
                          onClick={() => handleRemoveItem(item.item_name || item.name)}
                          disabled={loading}
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: 'var(--text-muted)', padding: 2, flexShrink: 0,
                            transition: 'color 0.2s',
                          }}
                          onMouseEnter={e => e.currentTarget.style.color = 'var(--danger)'}
                          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
                          title={`Remove ${item.item_name || item.name}`}
                        >
                          <Trash2 size={13} />
                        </button>
                      </motion.div>
                    ))}
                  </div>

                  {/* Totals footer */}
                  {effectiveOrder && (
                    <div style={{
                      padding: '12px 16px', borderTop: '1px solid var(--border-subtle)',
                      background: 'var(--bg-elevated)',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 3 }}>
                        <span>Subtotal</span>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>₹{effectiveOrder.subtotal}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>
                        <span>GST (5%)</span>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>₹{effectiveOrder.tax}</span>
                      </div>
                      <div style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        fontSize: 16, fontWeight: 800, fontFamily: 'var(--font-mono)',
                        color: 'var(--accent)',
                        borderTop: '1px solid var(--border-mid)', paddingTop: 8,
                      }}>
                        <span style={{ fontFamily: 'var(--font-body)' }}>Total</span>
                        <span>₹{effectiveOrder.total}</span>
                      </div>

                      {/* Quick confirm button */}
                      <motion.button
                        className="btn btn-primary"
                        onClick={handleConfirm}
                        disabled={loading}
                        style={{ width: '100%', marginTop: 10, fontSize: 13 }}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        {loading ? 'Confirming…' : `Confirm Order`}
                      </motion.button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
