import { useRef, useCallback, useState, useEffect } from 'react'

/**
 * useVoiceStream — WebSocket-based real-time voice streaming hook.
 * 
 * Connects to ws://localhost:8000/api/voice/stream and sends
 * audio chunks in real-time. Receives partial transcripts and
 * pipeline results as they become available.
 * 
 * Usage:
 *   const { connect, disconnect, sendAudioChunk, sendEnd, 
 *           partialTranscript, isConnected } = useVoiceStream({
 *     onPipelineResult: (result) => { ... },
 *     onTTSChunk: (audio_b64) => { ... },
 *     sessionId, language, restaurantId,
 *   })
 */

const WS_BASE = (() => {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_WS_BASE_URL) {
    return import.meta.env.VITE_WS_BASE_URL.replace(/\/$/, '')
  }
  if (typeof window !== 'undefined' && window.location) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}/api/voice`
  }
  return 'ws://localhost:3000/api/voice'
})()

export default function useVoiceStream({
  onPipelineResult,
  onTTSChunk,
  onError,
  sessionId,
  language,
  restaurantId,
} = {}) {
  const wsRef = useRef(null)
  const connectPromiseRef = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const [partialTranscript, setPartialTranscript] = useState('')
  const [finalTranscript, setFinalTranscript] = useState('')
  const callbacksRef = useRef({ onPipelineResult, onTTSChunk, onError })

  // Keep callbacks fresh without re-creating effects
  useEffect(() => {
    callbacksRef.current = { onPipelineResult, onTTSChunk, onError }
  })

  const sendConfig = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return false

    wsRef.current.send(JSON.stringify({
      type: 'config',
      session_id: sessionId,
      language: language !== 'auto' ? language : null,
      restaurant_id: restaurantId,
    }))
    return true
  }, [sessionId, language, restaurantId])

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      sendConfig()
      return true
    }

    if (connectPromiseRef.current) {
      return connectPromiseRef.current
    }

    connectPromiseRef.current = new Promise((resolve) => {
      const ws = new WebSocket(`${WS_BASE}/stream`)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        sendConfig()
        connectPromiseRef.current = null
        resolve(true)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          switch (data.type) {
            case 'partial_transcript':
              setPartialTranscript(data.text || '')
              break

            case 'final_transcript':
              setPartialTranscript('')
              setFinalTranscript(data.text || '')
              break

            case 'pipeline_result':
              setPartialTranscript('')
              if (callbacksRef.current.onPipelineResult) {
                callbacksRef.current.onPipelineResult(data)
              }
              break

            case 'tts_chunk':
              if (callbacksRef.current.onTTSChunk && data.audio_b64) {
                callbacksRef.current.onTTSChunk(data.audio_b64)
              }
              break

            case 'error':
              if (callbacksRef.current.onError) {
                callbacksRef.current.onError(data.detail || 'Stream error')
              }
              break

            case 'config_ack':
            case 'interrupted':
              break

            default:
              break
          }
        } catch {
          // Non-JSON message, ignore
        }
      }

      ws.onclose = () => {
        connectPromiseRef.current = null
        setIsConnected(false)
      }

      ws.onerror = () => {
        connectPromiseRef.current = null
        setIsConnected(false)
        if (callbacksRef.current.onError) {
          callbacksRef.current.onError('WebSocket connection failed')
        }
        resolve(false)
      }
    })

    return connectPromiseRef.current
  }, [sendConfig])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    connectPromiseRef.current = null
    setIsConnected(false)
    setPartialTranscript('')
  }, [])

  const sendAudioChunk = useCallback((chunk) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk)
    }
  }, [])

  const sendEnd = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end' }))
    }
  }, [])

  const sendInterrupt = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }))
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  return {
    connect,
    disconnect,
    sendConfig,
    sendAudioChunk,
    sendEnd,
    sendInterrupt,
    isConnected,
    partialTranscript,
    finalTranscript,
  }
}
