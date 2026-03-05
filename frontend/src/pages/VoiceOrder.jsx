import { useState } from 'react'
import { processVoiceText, processVoiceAudio, confirmOrder } from '../api/client'
import VoiceRecorder from '../components/VoiceRecorder'
import OrderSummary from '../components/OrderSummary'
import KOTTicket from '../components/KOTTicket'

export default function VoiceOrder() {
  const [result, setResult] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [kotData, setKotData] = useState(null)

  const handleTextOrder = async () => {
    if (!textInput.trim()) return
    setLoading(true)
    setConfirmed(false)
    setKotData(null)
    try {
      const data = await processVoiceText(textInput)
      setResult(data)
    } catch (err) {
      console.error('Text order failed:', err)
    }
    setLoading(false)
  }

  const handleAudioRecorded = async (audioBlob) => {
    setLoading(true)
    setConfirmed(false)
    setKotData(null)
    try {
      const data = await processVoiceAudio(audioBlob)
      setResult(data)
    } catch (err) {
      console.error('Voice order failed:', err)
    }
    setLoading(false)
  }

  const handleConfirm = async () => {
    if (!result?.order) return
    setLoading(true)
    try {
      const data = await confirmOrder(result.order)
      setConfirmed(true)
      setKotData(data.kot)
    } catch (err) {
      console.error('Confirm order failed:', err)
    }
    setLoading(false)
  }

  const handleDiscard = () => {
    setResult(null)
    setTextInput('')
    setConfirmed(false)
    setKotData(null)
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
            {result?.transcript && (
              <div style={{ marginTop: 16 }}>
                <span className="tag tag-blue" style={{ marginBottom: 8, display: 'inline-block' }}>Language Info</span>
                <p style={{ fontSize: 13, background: 'var(--surface2)', padding: '8px 12px', borderRadius: 4 }}>
                  {result.transcript}
                </p>
              </div>
            )}
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

      {/* Results */}
      {result && !confirmed && (
        <>
          <div className="grid-2">
            {/* Order Summary */}
            {result.order && (
              <div>
                <OrderSummary order={result.order} />
                <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
                  <button className="btn btn-primary" style={{ flex: 1, backgroundColor: 'var(--green)', borderColor: 'var(--green)' }} onClick={handleConfirm} disabled={loading}>
                    Confirm Order
                  </button>
                  <button className="btn btn-secondary" style={{ flex: 1 }} onClick={handleDiscard} disabled={loading}>
                    Discard
                  </button>
                </div>
              </div>
            )}

            {/* Upsell suggestions Banner */}
            {result.upsell_suggestions?.length > 0 && (
              <div className="card" style={{ marginTop: 16, borderColor: 'var(--orange)', borderWidth: 2 }}>
                <div className="card-header" style={{ color: 'var(--orange)', backgroundColor: 'rgba(255, 107, 53, 0.1)', fontWeight: 'bold' }}>⬆️ Upsell Suggestions</div>
                <div className="card-body">
                  {result.upsell_suggestions.map((u, i) => (
                    <div key={i} style={{ padding: '8px 0', borderBottom: i < result.upsell_suggestions.length - 1 ? '1px solid var(--border)' : 'none' }}>
                      <span style={{ fontSize: 14, fontWeight: 'bold', color: 'var(--orange)' }}>{u.suggestion_text}</span>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{u.reason}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Confirmed KOT display */}
      {confirmed && kotData && (
        <div style={{ maxWidth: 400, margin: '0 auto' }}>
          <KOTTicket kot={kotData} />
          <button className="btn btn-primary" style={{ width: '100%', marginTop: 16 }} onClick={handleDiscard}>
            New Order
          </button>
        </div>
      )}
    </div>
  )
}
