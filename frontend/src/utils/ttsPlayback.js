const LANGUAGE_MAP = {
  en: 'en-IN',
  hi: 'hi-IN',
  gu: 'gu-IN',
  mr: 'mr-IN',
  kn: 'kn-IN',
}

function decodeBase64Audio(base64Audio) {
  const binary = atob(base64Audio)
  const bytes = new Uint8Array(binary.length)

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }

  return bytes
}

export function stopBrowserSpeech() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return
  window.speechSynthesis.cancel()
}

export function speakWithBrowserTTS(text, language, { onStart, onEnd, onError } = {}) {
  if (typeof window === 'undefined' || !window.speechSynthesis || !text?.trim()) {
    onError?.()
    return false
  }

  stopBrowserSpeech()

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = LANGUAGE_MAP[language] || LANGUAGE_MAP.en
  utterance.onstart = () => onStart?.()
  utterance.onend = () => onEnd?.()
  utterance.onerror = () => onError?.()

  window.speechSynthesis.speak(utterance)
  return true
}

export function playAudioWithFallback({
  base64Audio,
  text,
  language,
  currentAudioRef,
  onStart,
  onEnd,
  onError,
}) {
  const finishWithBrowserTTS = () => {
    const spoke = speakWithBrowserTTS(text, language, { onStart, onEnd, onError })
    if (!spoke) onError?.()
  }

  if (!base64Audio) {
    finishWithBrowserTTS()
    return
  }

  try {
    const bytes = decodeBase64Audio(base64Audio)
    const blob = new Blob([bytes], { type: 'audio/mpeg' })
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    currentAudioRef.current = audio

    audio.onended = () => {
      URL.revokeObjectURL(url)
      currentAudioRef.current = null
      onEnd?.()
    }

    audio.onerror = () => {
      URL.revokeObjectURL(url)
      currentAudioRef.current = null
      finishWithBrowserTTS()
    }

    onStart?.()
    audio.play().catch(() => {
      URL.revokeObjectURL(url)
      currentAudioRef.current = null
      finishWithBrowserTTS()
    })
  } catch {
    currentAudioRef.current = null
    finishWithBrowserTTS()
  }
}
