import { useState, useRef, useEffect } from 'react'
import { Mic } from 'lucide-react'

const VISUALIZER_BARS = 48

export default function VoiceRecorder({ onRecorded }) {
  const [state, setState] = useState('idle') // idle | recording | processing
  const mediaRecorder = useRef(null)
  const chunks = useRef([])
  const analyserRef = useRef(null)
  const animFrameRef = useRef(null)
  const [levels, setLevels] = useState([0, 0, 0, 0, 0])
  const [time, setTime] = useState(0)
  const [barHeights, setBarHeights] = useState(
    Array.from({ length: VISUALIZER_BARS }, () => 4)
  )

  const isRecording = state === 'recording'
  const isProcessing = state === 'processing'

  // Cleanup animation frame on unmount
  useEffect(() => {
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [])

  // Timer: count seconds while recording
  useEffect(() => {
    let intervalId
    if (isRecording) {
      intervalId = setInterval(() => setTime(t => t + 1), 1000)
    } else {
      setTime(0)
    }
    return () => clearInterval(intervalId)
  }, [isRecording])

  // Randomise bars while recording for visual effect
  useEffect(() => {
    let frameId
    if (isRecording) {
      const animate = () => {
        setBarHeights(
          Array.from({ length: VISUALIZER_BARS }, () => 20 + Math.random() * 80)
        )
        frameId = requestAnimationFrame(animate)
      }
      frameId = requestAnimationFrame(animate)
    } else {
      setBarHeights(Array.from({ length: VISUALIZER_BARS }, () => 4))
    }
    return () => { if (frameId) cancelAnimationFrame(frameId) }
  }, [isRecording])

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

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const handleClick = () => {
    if (isProcessing) return
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return (
    <div className="ai-voice-wrap">
      {/* Mic / Stop button */}
      <button
        className={`ai-voice-btn${isRecording ? ' ai-voice-btn--active' : ''}`}
        type="button"
        onClick={handleClick}
        disabled={isProcessing}
      >
        {isProcessing ? (
          <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
        ) : isRecording ? (
          <div className="ai-voice-stop" />
        ) : (
          <Mic size={24} />
        )}
      </button>

      {/* Timer */}
      <span
        className="ai-voice-timer"
        style={{ opacity: isRecording ? 0.7 : 0.3 }}
      >
        {formatTime(time)}
      </span>

      {/* Visualizer bars */}
      <div className="ai-voice-bars">
        {Array.from({ length: VISUALIZER_BARS }).map((_, i) => (
          <div
            key={i}
            className={`ai-voice-bar${isRecording ? ' ai-voice-bar--active' : ''}`}
            style={
              isRecording
                ? {
                  height: `${barHeights[i]}%`,
                  animationDelay: `${i * 0.05}s`,
                }
                : { height: 4 }
            }
          />
        ))}
      </div>

      {/* Status label */}
      <p className="ai-voice-status">
        {isProcessing ? 'Processing…' : isRecording ? 'Listening...' : 'Click to speak'}
      </p>
    </div>
  )
}
