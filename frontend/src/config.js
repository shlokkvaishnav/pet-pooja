/**
 * Centralized configuration for the frontend.
 * All values are overridable via VITE_* environment variables.
 */

// API
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
export const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT || 30000)
export const API_AUDIO_TIMEOUT = Number(import.meta.env.VITE_API_AUDIO_TIMEOUT || 120000)

// Cache (ms)
export const SHORT_CACHE_TTL = Number(import.meta.env.VITE_CACHE_SHORT_TTL || 20000)
export const DEFAULT_CACHE_TTL = Number(import.meta.env.VITE_CACHE_DEFAULT_TTL || 45000)
export const LONG_CACHE_TTL = Number(import.meta.env.VITE_CACHE_LONG_TTL || 120000)
export const MAX_CACHE_ENTRIES = Number(import.meta.env.VITE_CACHE_MAX_ENTRIES || 200)

// Voice Recorder
export const VOICE_VISUALIZER_BARS = Number(import.meta.env.VITE_VOICE_VISUALIZER_BARS || 48)
export const VOICE_SPEECH_THRESHOLD = Number(import.meta.env.VITE_VOICE_SPEECH_THRESHOLD || 12)
export const VOICE_SILENCE_TIMEOUT_MS = Number(import.meta.env.VITE_VOICE_SILENCE_TIMEOUT_MS || 800)
export const VOICE_MAX_WAIT_NO_SPEECH_MS = Number(import.meta.env.VITE_VOICE_MAX_WAIT_NO_SPEECH_MS || 2500)
export const VOICE_MAX_RECORD_MS = Number(import.meta.env.VITE_VOICE_MAX_RECORD_MS || 10000)
export const VOICE_AUTO_LISTEN_DELAY_MS = Number(import.meta.env.VITE_VOICE_AUTO_LISTEN_DELAY_MS || 600)

// Revenue Insights
export const TARGET_UPSELL_CM = Number(import.meta.env.VITE_TARGET_UPSELL_CM || 65)
export const MIN_ORDER_HISTORY = Number(import.meta.env.VITE_MIN_ORDER_HISTORY || 30)

// Pagination
export const ORDERS_PAGE_LIMIT = Number(import.meta.env.VITE_ORDERS_PAGE_LIMIT || 20)
export const INVENTORY_PAGE_LIMIT = Number(import.meta.env.VITE_INVENTORY_PAGE_LIMIT || 25)

// Locale / Currency
export const NUMBER_LOCALE = import.meta.env.VITE_NUMBER_LOCALE || 'en-IN'
export const CURRENCY_SYMBOL = import.meta.env.VITE_CURRENCY_SYMBOL || '₹'

// Contact Info
export const CONTACT_EMAIL = import.meta.env.VITE_CONTACT_EMAIL || 'hello@sizzle.ai'
export const CONTACT_PHONE = import.meta.env.VITE_CONTACT_PHONE || '+91 98765 43210'
export const CONTACT_LOCATION = import.meta.env.VITE_CONTACT_LOCATION || 'Pune, Maharashtra, India'

// Demo Mode
export const DEMO_MODE = (import.meta.env.VITE_DEMO_MODE || 'true') === 'true'

// Retry
export const TRANSIENT_HTTP_STATUSES = new Set([408, 425, 429, 500, 502, 503, 504])
