import { useState, useRef, useEffect } from 'react'

export default function VoiceRecorder({ onRecorded, onStartRecording }) {
  const [state, setState] = useState('idle') // idle | recording | processing
  const mediaRecorder = useRef(null)
  const chunks = useRef([])
  const analyserRef = useRef(null)
  const animFrameRef = useRef(null)
  const [levels, setLevels] = useState([0, 0, 0, 0, 0])

  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [])

  const updateLevels = (analyser) => {
    const data = new Uint8Array(analyser.frequencyBinCount)
    const tick = () => {
      analyser.getByteFrequencyData(data)
      const step = Math.floor(data.length / 5)
      const newLevels = Array.from({ length: 5 }, (_, i) => {
        const slice = data.slice(i * step, (i + 1) * step)
        const avg = slice.reduce((a, b) => a + b, 0) / slice.length
        return Math.min(avg / 255, 1)
      })
      setLevels(newLevels)
      animFrameRef.current = requestAnimationFrame(tick)
    }
    tick()
  }

  const startRecording = async () => {
    try {
      // Notify parent to stop any playing audio (interrupt)
      if (onStartRecording) onStartRecording()

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = { audioCtx, analyser }

      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorder.current = recorder
      chunks.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }

      recorder.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        stream.getTracks().forEach(t => t.stop())
        if (analyserRef.current?.audioCtx) analyserRef.current.audioCtx.close()
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
        setLevels([0, 0, 0, 0, 0])
        setState('processing')
        if (onRecorded) {
          Promise.resolve(onRecorded(blob)).finally(() => setState('idle'))
        }
      }

      recorder.start()
      setState('recording')
      updateLevels(analyser)
    } catch (err) {
      console.error('Mic access failed:', err)
      alert('Microphone access denied. Please allow microphone access.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      mediaRecorder.current.stop()
    }
  }

  const isRecording = state === 'recording'
  const isProcessing = state === 'processing'

  const btnBg = isRecording
    ? 'linear-gradient(135deg, #f87171, #ef4444)'
    : isProcessing
    ? 'linear-gradient(135deg, var(--bg-overlay), var(--bg-elevated))'
    : 'linear-gradient(135deg, var(--accent), #e55a28)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
      {/* Audio level bars */}
      <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 32 }}>
        {levels.map((l, i) => (
          <div
            key={i}
            style={{
              width: 4,
              height: `${Math.max(4, l * 32)}px`,
              borderRadius: 2,
              background: isRecording ? 'var(--accent)' : 'var(--bg-overlay)',
              transition: 'height 0.08s ease',
            }}
          />
        ))}
      </div>

      {/* Main button */}
      <button
        onClick={isRecording ? stopRecording : isProcessing ? undefined : startRecording}
        disabled={isProcessing}
        style={{
          width: 72,
          height: 72,
          borderRadius: '50%',
          border: '2px solid transparent',
          background: btnBg,
          color: 'white',
          fontSize: 24,
          cursor: isProcessing ? 'wait' : 'pointer',
          boxShadow: isRecording
            ? '0 0 0 6px rgba(248,113,113,0.15)'
            : '0 0 0 3px rgba(200,69,10,0.1)',
          transition: 'box-shadow 0.3s, transform 0.15s',
          animation: isRecording ? 'voicePulse 1.5s ease-in-out infinite' : 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {isProcessing ? (
          <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
        ) : isRecording ? '⏹' : '🎤'}
      </button>

      {/* State label */}
      <span style={{
        fontSize: 11,
        fontFamily: 'var(--font-body)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: isRecording ? 'var(--danger)' : isProcessing ? 'var(--text-muted)' : 'var(--text-secondary)',
      }}>
        {isRecording ? 'Listening…' : isProcessing ? 'Processing…' : 'Tap to speak'}
      </span>
    </div>
  )
}
