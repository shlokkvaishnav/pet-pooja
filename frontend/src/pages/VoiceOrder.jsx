import { useState, useRef } from 'react'
import { submitTextOrder, submitVoiceOrder, confirmOrder } from '../api/client'
import VoiceRecorder from '../components/VoiceRecorder'
import OrderSummary from '../components/OrderSummary'
import KOTTicket from '../components/KOTTicket'

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
      const detail = err.response?.data?.detail || 'Order processing failed'
      setError(detail)
    }
    setLoading(false)
  }

  const handleAudioRecorded = async (audioBlob) => {
    setLoading(true)
    setError(null)
    try {
      const data = await submitVoiceOrder(audioBlob, sessionId.current)
      setResult(data)
    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail || 'Voice processing failed'
      if (status === 503) {
        setError('Speech recognition is unavailable. Please try text input.')
      } else if (status === 422) {
        setError('Could not understand the order. Please try again.')
      } else {
        setError(detail)
      }
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

  const confidenceColor = (conf) => {
    if (conf >= 0.9) return 'var(--green, #22c55e)'
    if (conf >= 0.85) return 'var(--yellow, #eab308)'
    return 'var(--red, #ef4444)'
  }

  return (
    <div>
      <div className="page-header">
        <h1>Voice Order</h1>
        <p>Speak or type an order in English, Hindi, or Hinglish</p>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Voice Input */}
        <div className="card">
          <div className="card-header">🎙️ Voice Input</div>
          <div className="card-body" style={{ textAlign: 'center', padding: 32 }}>
            <VoiceRecorder onRecorded={handleAudioRecorded} />
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>
              Click to record, click again to stop
            </p>
          </div>
        </div>

        {/* Text Input */}
        <div className="card">
          <div className="card-header">⌨️ Text Input</div>
          <div className="card-body">
            <textarea
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="e.g. ek paneer tikka aur do butter naan, extra spicy"
              style={{
                width: '100%',
                height: 80,
                padding: 12,
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text)',
                fontFamily: 'var(--font)',
                fontSize: 13,
                resize: 'vertical',
              }}
            />
            <button
              className="btn btn-primary"
              onClick={handleTextOrder}
              disabled={loading || !textInput.trim()}
              style={{ marginTop: 12, width: '100%' }}
            >
              {loading ? 'Processing...' : 'Process Order'}
            </button>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card" style={{ marginBottom: 16, borderColor: 'var(--red, #ef4444)' }}>
          <div className="card-body" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <p style={{ color: 'var(--red, #ef4444)', fontSize: 13, margin: 0 }}>⚠️ {error}</p>
            <button
              onClick={() => setError(null)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 16 }}
            >×</button>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Parsed info */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">📝 Parsed Input</div>
            <div className="card-body">
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Transcript: </span>
                <span style={{ fontSize: 13 }}>{result.transcript}</span>
              </div>
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Normalized: </span>
                <span style={{ fontSize: 13 }}>{result.normalized}</span>
              </div>
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Intent: </span>
                <span className={`tag tag-${result.intent === 'ORDER' ? 'star' : 'puzzle'}`}>
                  {result.intent}
                </span>
              </div>
              {result.detected_language && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Language: </span>
                  <span style={{ fontSize: 13 }}>{result.detected_language}</span>
                </div>
              )}
              {result.session_id && (
                <div>
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Session: </span>
                  <span style={{ fontSize: 11, fontFamily: 'monospace' }}>{result.session_id}</span>
                  {result.turn_count > 1 && (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
                      (turn {result.turn_count})
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Matched Items with Confidence */}
          {result.items?.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">🎯 Matched Items</div>
              <div className="card-body">
                {result.items.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <div>
                      <span style={{ fontSize: 13, fontWeight: 600 }}>
                        {item.quantity}× {item.item_name}
                      </span>
                      <span style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: 'white',
                        padding: '2px 6px',
                        borderRadius: 4,
                        marginLeft: 8,
                        background: confidenceColor(item.confidence),
                      }}>
                        {Math.round(item.confidence * 100)}%
                      </span>
                    </div>
                    <span style={{ fontWeight: 600 }}>₹{item.line_total}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Disambiguation Warning */}
          {result.needs_clarification && result.disambiguation?.length > 0 && (
            <div className="card" style={{ marginBottom: 16, borderColor: 'var(--yellow, #eab308)' }}>
              <div className="card-header" style={{ color: 'var(--yellow, #eab308)' }}>
                ⚠️ Did you mean...?
              </div>
              <div className="card-body">
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                  Some items had low match confidence. Please verify or re-order:
                </p>
                {result.disambiguation.map((d, idx) => (
                  <div key={idx} style={{ marginBottom: 12 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                      Matched: "{d.item_name}" ({Math.round(d.confidence * 100)}% confidence)
                    </div>
                    {d.alternatives?.length > 0 && (
                      <div style={{ paddingLeft: 12 }}>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Alternatives: </span>
                        {d.alternatives.map((alt, ai) => (
                          <span key={ai} style={{ fontSize: 12, marginRight: 12 }}>
                            {alt.item_name} ({Math.round(alt.confidence * 100)}%)
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Items Warning */}
          {result.needs_clarification && (!result.disambiguation || result.disambiguation.length === 0) && (
            <div className="card" style={{ marginBottom: 16, borderColor: 'var(--yellow, #eab308)' }}>
              <div className="card-body">
                <p style={{ color: 'var(--yellow, #eab308)', fontSize: 13 }}>
                  ⚠️ No menu items were recognized. Please try rephrasing your order.
                </p>
              </div>
            </div>
          )}

          {/* Session Accumulated Items */}
          {result.session_items?.length > result.items?.length && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">📋 Full Cart (all turns)</div>
              <div className="card-body">
                {result.session_items.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 13 }}>
                    <span>{item.quantity}× {item.item_name}</span>
                    <span>₹{item.line_total}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid-2">
            {/* Order Summary */}
            {result.order && <OrderSummary order={result.order} />}

            {/* KOT Ticket */}
            {result.kot && <KOTTicket kot={result.kot} />}
          </div>

          {/* Upsell suggestions */}
          {result.upsell_suggestions?.length > 0 && (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-header">⬆️ Upsell Suggestions</div>
              <div className="card-body">
                {result.upsell_suggestions.map((u, idx) => (
                  <div key={idx} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 13 }}>{u.name || u.suggestion_text}</span>
                    {u.reason && (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 8 }}>
                        — {u.reason}
                      </span>
                    )}
                    {u.selling_price && (
                      <span style={{ fontSize: 12, fontWeight: 600, marginLeft: 8 }}>
                        ₹{u.selling_price}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          {result.order && !result.confirmed && (
            <div style={{ marginTop: 16, display: 'flex', gap: 12 }}>
              <button
                className="btn btn-primary"
                onClick={handleConfirm}
                disabled={loading || result.needs_clarification}
                style={{ flex: 1 }}
              >
                {loading ? 'Confirming...' : '✅ Confirm Order'}
              </button>
              <button
                className="btn"
                onClick={handleNewOrder}
                style={{ flex: 1, background: 'var(--surface2)', color: 'var(--text)' }}
              >
                🔄 New Order
              </button>
            </div>
          )}

          {result.confirmed && (
            <div className="card" style={{ marginTop: 16, borderColor: 'var(--green, #22c55e)' }}>
              <div className="card-body" style={{ textAlign: 'center', padding: 24 }}>
                <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--green, #22c55e)' }}>
                  ✅ Order Confirmed!
                </p>
                <button
                  className="btn btn-primary"
                  onClick={handleNewOrder}
                  style={{ marginTop: 12 }}
                >
                  Start New Order
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
