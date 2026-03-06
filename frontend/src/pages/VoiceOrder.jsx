import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { submitTextOrder, transcribeAudio, confirmOrder, getMenuMatrix, getTrends } from '../api/client'
import VoiceRecorder from '../components/VoiceRecorder'
import OrderSummary from '../components/OrderSummary'
import KOTTicket from '../components/KOTTicket'
import { motion, AnimatePresence } from 'motion/react'
import { StaggerReveal, staggerContainer, staggerItem } from '../utils/animations'
import { Trash2, ShoppingCart, ClipboardList, CheckCircle } from 'lucide-react'
import { buildUpsellCandidates } from '../utils/revenueInsights'

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
  const [confirmedOrders, setConfirmedOrders] = useState([]) // Array of confirmed order snapshots
  const [autoListenEnabled, setAutoListenEnabled] = useState(true)
  const [selectedLanguage, setSelectedLanguage] = useState('auto') // 'auto'|'en'|'hi'|'gu'|'mr'|'kn'
  const [menuItems, setMenuItems] = useState([])
  const [trendData, setTrendData] = useState(null)
  const sessionId = useRef(generateSessionId())
  const currentAudioRef = useRef(null)
  const recorderRef = useRef(null)
  const autoListenRef = useRef(true)
  const lastIntentRef = useRef(null)

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
      // Auto-listen: restart recording after TTS finishes (skip after CONFIRM)
      if (autoListenRef.current && lastIntentRef.current !== 'CONFIRM') {
        setTimeout(() => recorderRef.current?.startRecording(), 600)
      }
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

    // Track last intent for auto-listen decisions
    lastIntentRef.current = data.intent
    // Keep autoListenRef in sync
    autoListenRef.current = autoListenEnabled

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
    } else if (intent === 'DONE') {
      setActionFeedback({ type: 'info', message: data.tts_text || 'Should I place the order?' })
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

    // Auto-confirm if voice said "confirm" and cart has items
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
      const langToSend = selectedLanguage !== 'auto' ? selectedLanguage : null
      const data = await transcribeAudio(audioBlob, sessionId.current, langToSend)
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
      // Save confirmed order to orders list
      setConfirmedOrders(prev => [{
        id: orderToConfirm.order_id || `ORD-${Date.now()}`,
        items: [...(data.session_items || data.items || [])],
        order: { ...orderToConfirm },
        confirmedAt: new Date().toLocaleTimeString(),
      }, ...prev])
      // Reset for new order
      setResult(null)
      setActionFeedback({ type: 'confirm', message: 'Order confirmed! KOT sent to kitchen.' })
      sessionId.current = generateSessionId()
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
      // Save confirmed order to orders list
      setConfirmedOrders(prev => [{
        id: orderToConfirm.order_id || `ORD-${Date.now()}`,
        items: [...(result.session_items || result.items || [])],
        order: { ...orderToConfirm },
        confirmedAt: new Date().toLocaleTimeString(),
      }, ...prev])
      // Reset for new order
      setResult(null)
      setActionFeedback({ type: 'confirm', message: 'Order confirmed! KOT sent to kitchen.' })
      sessionId.current = generateSessionId()
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
    sessionId.current = generateSessionId()
  }

  // ── Auto-listen silence callback ──
  const handleAutoListenSilence = useCallback(() => {
    // Silence detected with no speech during auto-listen — do nothing, stay idle
  }, [])

  // Keep autoListenRef in sync with state
  useEffect(() => {
    autoListenRef.current = autoListenEnabled
  }, [autoListenEnabled])

  useEffect(() => {
    let active = true
    Promise.all([
      getMenuMatrix().catch(() => ({ items: [] })),
      getTrends().catch(() => null),
    ]).then(([matrix, trends]) => {
      if (!active) return
      setMenuItems(matrix?.items || [])
      setTrendData(trends)
    })
    return () => {
      active = false
    }
  }, [])

  const confColor = (c) => c >= 0.9 ? 'var(--success)' : c >= 0.85 ? 'var(--warning)' : 'var(--danger)'

  // Cart items from session (accumulated across all turns)
  // Fallback to result.items if session_items not available (e.g. session_id missed)
  const cartItems = result?.session_items || result?.items || []
  const hasCart = cartItems.length > 0
  const suggestedAddOns = useMemo(() => (
    buildUpsellCandidates({
      items: menuItems,
      trends: trendData,
      currentOrderItems: cartItems,
      limit: 3,
    })
  ), [menuItems, trendData, cartItems])

  // Effective order for display (use session_order which covers all turns)
  const effectiveOrder = result?.session_order || result?.order

  // Determine step: 1=Listen, 2=Review (with continued input)
  const step = result ? 2 : 1

  // Feedback colors
  const feedbackStyles = {
    add: { bg: 'color-mix(in srgb, var(--success) 12%, transparent)', color: 'var(--success)', icon: '+' },
    cancel: { bg: 'color-mix(in srgb, var(--danger) 12%, transparent)', color: 'var(--danger)', icon: '−' },
    modify: { bg: 'color-mix(in srgb, var(--warning) 12%, transparent)', color: 'var(--warning)', icon: '↻' },
    confirm: { bg: 'color-mix(in srgb, var(--success) 12%, transparent)', color: 'var(--success)', icon: '✓' },
    info: { bg: 'color-mix(in srgb, var(--accent) 12%, transparent)', color: 'var(--accent)', icon: 'ℹ' },
  }

  const handleAddSuggestedAddon = async (addon) => {
    if (!addon?.name) return
    setLoading(true)
    setError(null)
    try {
      const data = await submitTextOrder(`add one ${addon.name}`, sessionId.current)
      processResult(data)
      setActionFeedback({ type: 'add', message: `Added add-on: ${addon.name}` })
    } catch (err) {
      setError(err.response?.data?.detail || err.detail || `Failed to add ${addon.name}`)
    }
    setLoading(false)
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
        {['Listen', 'Review'].map((label, i) => {
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
        {confirmedOrders.length > 0 && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle size={14} style={{ color: 'var(--success)' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--success)' }}>
              {confirmedOrders.length} order{confirmedOrders.length > 1 ? 's' : ''} placed
            </span>
          </div>
        )}
      </div>

      {/* ── Voice/Text Input — always visible ── */}
      {step <= 2 && (
        <StaggerReveal className="grid-2" style={{ marginBottom: 24 }} variants={staggerContainer}>
          <motion.div className="card" variants={staggerItem}>
            <div className="card-header">
              Voice Input
              {hasCart && <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}> — say "remove", "add", or "confirm"</span>}
            </div>
            {/* Language selector */}
            <div style={{ display: 'flex', gap: 4, padding: '8px 16px 0', flexWrap: 'wrap' }}>
              {[
                { code: 'auto', label: 'Auto' },
                { code: 'en',   label: 'EN' },
                { code: 'hi',   label: 'हिं' },
                { code: 'gu',   label: 'ગુ' },
                { code: 'mr',   label: 'मर' },
                { code: 'kn',   label: 'ಕನ' },
              ].map(({ code, label }) => (
                <button
                  key={code}
                  onClick={() => setSelectedLanguage(code)}
                  style={{
                    padding: '3px 10px', borderRadius: 'var(--radius-full)', fontSize: 11, fontWeight: 600,
                    cursor: 'pointer', border: '1px solid',
                    borderColor: selectedLanguage === code ? 'var(--accent)' : 'var(--border-subtle)',
                    background: selectedLanguage === code
                      ? 'color-mix(in srgb, var(--accent) 15%, transparent)'
                      : 'var(--bg-elevated)',
                    color: selectedLanguage === code ? 'var(--accent)' : 'var(--text-muted)',
                    transition: 'all 0.15s',
                  }}
                >
                  {label}
                </button>
              ))}
              <span style={{ fontSize: 10, color: 'var(--text-muted)', alignSelf: 'center', marginLeft: 4 }}>
                {selectedLanguage === 'auto' ? 'auto-detect' : 'language locked'}
              </span>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: 32 }}>
              <VoiceRecorder
                ref={recorderRef}
                onRecorded={handleAudioRecorded}
                onStartRecording={handleInterruptAudio}
                autoListen={autoListenEnabled}
                onAutoListenSilence={handleAutoListenSilence}
              />
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
        {actionFeedback && (
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
        {result && (
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
              <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                Parsed Input
                <span style={{
                  fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
                  padding: '2px 6px', borderRadius: 'var(--radius-full)',
                  background: 'color-mix(in srgb, var(--warning) 18%, transparent)',
                  color: 'var(--warning)', border: '1px solid var(--warning)',
                  textTransform: 'uppercase',
                }}>TEST</span>
              </div>
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
                <div className="card-header" style={{ color: 'var(--warning)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  Did you mean…?
                  <span style={{
                    fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
                    padding: '2px 6px', borderRadius: 'var(--radius-full)',
                    background: 'color-mix(in srgb, var(--warning) 18%, transparent)',
                    color: 'var(--warning)', border: '1px solid var(--warning)',
                    textTransform: 'uppercase',
                  }}>TEST</span>
                </div>
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
            {hasCart && (
              <motion.div
                className="card" style={{ marginBottom: 16, marginLeft: 'auto', width: '100%', maxWidth: 440 }}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4, duration: 0.4 }}
              >
                <div className="card-header">Suggested Add-ons</div>
                <div className="card-body">
                  {suggestedAddOns.length === 0 ? (
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      No high-confidence add-ons yet. Continue building the order for better recommendations.
                    </div>
                  ) : suggestedAddOns.map((u) => (
                    <div key={u.item_id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 13, color: 'var(--text-primary)', fontWeight: 600 }}>{u.name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.reason}</div>
                      </div>
                      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontSize: 11, color: 'var(--success)', fontWeight: 700 }}>CM {u.cm_percent.toFixed(1)}%</span>
                        <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontWeight: 600 }}>Rs {u.price}</span>
                        <button className="btn btn-ghost" style={{ fontSize: 11 }} disabled={loading} onClick={() => handleAddSuggestedAddon(u)}>
                          Add to Order
                        </button>
                      </div>
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

      {/* ── Confirmed Orders Table ── */}
      <AnimatePresence>
        {confirmedOrders.length > 0 && (
          <motion.div
            className="card" style={{ marginTop: 24 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <ClipboardList size={14} />
              <span>Placed Orders</span>
              <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginLeft: 'auto' }}>
                {confirmedOrders.length} order{confirmedOrders.length > 1 ? 's' : ''}
              </span>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {confirmedOrders.map((order, orderIdx) => (
                <motion.div
                  key={order.id}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: orderIdx * 0.1 }}
                  style={{
                    borderBottom: orderIdx < confirmedOrders.length - 1 ? '2px solid var(--border-mid)' : 'none',
                  }}
                >
                  {/* Order header */}
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '10px 16px',
                    background: 'var(--bg-elevated)',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <CheckCircle size={14} style={{ color: 'var(--success)' }} />
                      <span style={{ fontSize: 13, fontWeight: 700, fontFamily: 'var(--font-display)' }}>
                        {order.id}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {order.confirmedAt}
                      </span>
                      <span style={{ fontSize: 14, fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>
                        ₹{order.order.total}
                      </span>
                    </div>
                  </div>

                  {/* Order items */}
                  <table className="data-table" style={{ marginBottom: 0 }}>
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th style={{ textAlign: 'center' }}>Qty</th>
                        <th style={{ textAlign: 'right' }}>Price</th>
                        <th style={{ textAlign: 'right' }}>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {order.items.map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: 13 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              {item.is_veg !== undefined && (
                                <span style={{
                                  width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                                  background: item.is_veg ? '#22c55e' : '#ef4444',
                                }} />
                              )}
                              <span>{item.item_name || item.name}</span>
                            </div>
                            {item.modifiers?.spice_level && item.modifiers.spice_level !== 'medium' && (
                              <span style={{
                                fontSize: 10, padding: '1px 5px', borderRadius: 'var(--radius-full)',
                                background: 'var(--warning-subtle)', color: 'var(--warning)', marginLeft: 14,
                              }}>🌶️ {item.modifiers.spice_level}</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 12 }}>{item.quantity}</td>
                          <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-muted)' }}>₹{item.unit_price}</td>
                          <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 12 }}>₹{item.line_total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {/* Order totals */}
                  <div style={{ padding: '8px 16px', display: 'flex', justifyContent: 'flex-end', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                    <span>Sub: ₹{order.order.subtotal}</span>
                    <span>GST: ₹{order.order.tax}</span>
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Total: ₹{order.order.total}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </motion.div>
  )
}
