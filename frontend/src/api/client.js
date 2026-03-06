import axios from 'axios'
import {
  API_BASE_URL,
  API_TIMEOUT,
  API_AUDIO_TIMEOUT,
  SHORT_CACHE_TTL,
  DEFAULT_CACHE_TTL,
  LONG_CACHE_TTL,
  MAX_CACHE_ENTRIES,
  TRANSIENT_HTTP_STATUSES,
} from '../config'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
})

const inflightGets = new Map()
const responseCache = new Map()

const SHORT_CACHE_TTL_MS = SHORT_CACHE_TTL
const DEFAULT_CACHE_TTL_MS = DEFAULT_CACHE_TTL
const LONG_CACHE_TTL_MS = LONG_CACHE_TTL
const MAX_CACHE_ENTRIES_LIMIT = MAX_CACHE_ENTRIES
const TRANSIENT_STATUS = TRANSIENT_HTTP_STATUSES

function normalizeError(error) {
  const status = error?.response?.status
  const data = error?.response?.data
  const detail = data?.detail || data?.error || error?.message || 'An unknown API error occurred.'
  return { status, detail, raw: data || null }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function toSortedParams(params = {}) {
  const entries = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .sort(([a], [b]) => a.localeCompare(b))
  return Object.fromEntries(entries)
}

function makeGetKey(path, params = {}) {
  return `${path}?${JSON.stringify(toSortedParams(params))}`
}

function readCache(key) {
  const entry = responseCache.get(key)
  if (!entry) return null
  if (Date.now() - entry.ts > entry.ttlMs) {
    responseCache.delete(key)
    return null
  }
  return entry.data
}

function writeCache(key, data, ttlMs = DEFAULT_CACHE_TTL_MS) {
  if (responseCache.size >= MAX_CACHE_ENTRIES_LIMIT && !responseCache.has(key)) {
    const oldestKey = responseCache.keys().next().value
    if (oldestKey) responseCache.delete(oldestKey)
  }
  responseCache.set(key, { data, ts: Date.now(), ttlMs })
}

function invalidateCacheByPrefix(prefix) {
  for (const key of responseCache.keys()) {
    if (key.startsWith(prefix)) responseCache.delete(key)
  }
}

async function requestWithRetry(fn, retries = 1) {
  let attempt = 0
  while (true) {
    try {
      return await fn()
    } catch (error) {
      const status = error?.response?.status
      const transient = !status || TRANSIENT_STATUS.has(status)
      if (!transient || attempt >= retries) throw error
      await sleep(200 * (2 ** attempt))
      attempt += 1
    }
  }
}

async function getWithCache(path, {
  params = {},
  ttlMs = DEFAULT_CACHE_TTL_MS,
  dedupe = true,
  retries = 1,
  bypassCache = false,
} = {}) {
  const sortedParams = toSortedParams(params)
  const key = makeGetKey(path, sortedParams)

  if (!bypassCache) {
    const cached = readCache(key)
    if (cached !== null) return cached
  }

  if (dedupe && inflightGets.has(key)) {
    return inflightGets.get(key)
  }

  const reqPromise = requestWithRetry(
    () => api.get(path, { params: sortedParams }).then((r) => r.data),
    retries,
  )
    .then((data) => {
      writeCache(key, data, ttlMs)
      return data
    })
    .catch((error) => {
      console.error('API Error:', error?.response?.data || error.message)
      throw normalizeError(error)
    })
    .finally(() => {
      inflightGets.delete(key)
    })

  if (dedupe) inflightGets.set(key, reqPromise)
  return reqPromise
}

async function post(path, body) {
  try {
    return await api.post(path, body).then((r) => r.data)
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

async function patch(path, body) {
  try {
    return await api.patch(path, body).then((r) => r.data)
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

function _rid() {
  try {
    const r = JSON.parse(localStorage.getItem('sizzle_restaurant') || '{}')
    return r.restaurant_id || null
  } catch {
    return null
  }
}

function _params(extra = {}) {
  const rid = _rid()
  return rid ? { restaurant_id: rid, ...extra } : extra
}

export const loginApi = (email, password) =>
  post('/auth/login', { email, password })

export const getRestaurantProfile = (restaurantId) =>
  getWithCache(`/auth/me/${restaurantId}`, { ttlMs: LONG_CACHE_TTL_MS })

export const updateRestaurantProfile = (restaurantId, payload) =>
  patch(`/auth/me/${restaurantId}`, payload)

export const getDashboardMetrics = () =>
  getWithCache('/revenue/dashboard', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getMenuMatrix = () =>
  getWithCache('/revenue/menu-matrix', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getHiddenStars = () =>
  getWithCache('/revenue/hidden-stars', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getRisks = () =>
  getWithCache('/revenue/risks', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getCombos = (forceRetrain = false, discountPct = 10) =>
  getWithCache('/revenue/combos', {
    params: _params({ force_retrain: forceRetrain, discount_pct: discountPct }),
    ttlMs: SHORT_CACHE_TTL_MS,
    bypassCache: !!forceRetrain,
  })

export const getPriceRecommendations = () =>
  getWithCache('/revenue/price-recommendations', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getCategoryBreakdown = () =>
  getWithCache('/revenue/category-breakdown', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getTrends = () =>
  getWithCache('/revenue/trends', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getWowMom = () =>
  getWithCache('/revenue/trends/wow-mom', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getPriceElasticity = () =>
  getWithCache('/revenue/trends/price-elasticity', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getCannibalization = (days = 90) =>
  getWithCache('/revenue/analytics/cannibalization', { params: _params({ days }), ttlMs: SHORT_CACHE_TTL_MS })

export const getPriceSensitivity = () =>
  getWithCache('/revenue/analytics/price-sensitivity', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getWasteAnalysis = (days = 30) =>
  getWithCache('/revenue/analytics/waste', { params: _params({ days }), ttlMs: SHORT_CACHE_TTL_MS })

export const getCustomerReturns = (days = 30) =>
  getWithCache('/revenue/analytics/customer-returns', { params: _params({ days }), ttlMs: SHORT_CACHE_TTL_MS })

export const getMenuComplexity = () =>
  getWithCache('/revenue/analytics/menu-complexity', { params: _params(), ttlMs: SHORT_CACHE_TTL_MS })

export const getOperationalMetrics = (days = 30) =>
  getWithCache('/revenue/analytics/operational', { params: _params({ days }), ttlMs: SHORT_CACHE_TTL_MS })

export const transcribeAudio = (audioBlob, sessionId, language = null) => {
  const form = new FormData()
  if (audioBlob) {
    form.append('audio', audioBlob, 'recording.webm')
  }
  if (sessionId) {
    form.append('session_id', sessionId)
  }
  if (language) {
    form.append('language', language)
  }
  const rid = _rid()
  if (rid) {
    form.append('restaurant_id', String(rid))
  }
  // Audio processing involves STT model inference + TTS — can take 30-60s on first call
  return api.post('/voice/process-audio', form, { timeout: API_AUDIO_TIMEOUT }).then(r => r.data)
}

export const submitTextOrder = (text, sessionId) =>
  post('/voice/process', { text, session_id: sessionId || null, restaurant_id: _rid() })

export const confirmOrder = (order, kot) =>
  api.post('/voice/confirm-order', { order, kot }, { params: _params() }).then(r => r.data)

export const speakText = (text, language = 'en') =>
  post('/voice/speak', { text, language })

export const getVoiceOrders = () =>
  getWithCache('/voice/orders', { ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsOrders = (params = {}) =>
  getWithCache('/ops/orders', { params, ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsOrder = (orderId) =>
  getWithCache(`/ops/orders/${orderId}`, { ttlMs: SHORT_CACHE_TTL_MS })

export const createOpsOrder = (payload) =>
  api.post('/ops/orders', payload, { params: _params() }).then(r => r.data).then((data) => {
    invalidateCacheByPrefix('/ops/orders?')
    return data
  })

export const updateOpsOrder = (orderId, payload) =>
  patch(`/ops/orders/${orderId}`, payload).then((data) => {
    invalidateCacheByPrefix('/ops/orders?')
    invalidateCacheByPrefix('/ops/tables?')
    return data
  })

export const cancelOpsOrder = (orderId) =>
  post(`/ops/orders/${orderId}/cancel`, {}).then((data) => {
    invalidateCacheByPrefix('/ops/orders?')
    invalidateCacheByPrefix('/ops/tables?')
    return data
  })

export const getOpsTables = () =>
  getWithCache('/ops/tables', { ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsTablesFiltered = (params = {}) =>
  getWithCache('/ops/tables', { params, ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsInventory = (days = 30) =>
  getWithCache('/ops/inventory', { params: { days }, ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsInventoryFiltered = (params = {}) =>
  getWithCache('/ops/inventory', { params, ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsReports = (days = 14) =>
  getWithCache('/ops/reports', { params: { days }, ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsReportsFiltered = (params = {}) =>
  getWithCache('/ops/reports', { params, ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsSettings = () =>
  getWithCache('/ops/settings', { params: _params(), ttlMs: LONG_CACHE_TTL_MS })

export const updateOpsSettings = (payload) =>
  patch('/ops/settings', _params(payload)).then((data) => {
    invalidateCacheByPrefix('/ops/settings?')
    return data
  })

export const createSettingsStaff = (payload) =>
  post('/ops/settings/staff', _params(payload)).then((data) => {
    invalidateCacheByPrefix('/ops/settings?')
    return data
  })

export const updateSettingsStaff = (staffId, payload) =>
  patch(`/ops/settings/staff/${staffId}`, payload).then((data) => {
    invalidateCacheByPrefix('/ops/settings?')
    return data
  })

export const updateTableStatus = (tableId, payload) =>
  patch(`/ops/tables/${tableId}`, payload).then((data) => {
    invalidateCacheByPrefix('/ops/tables?')
    return data
  })

export const previewTableMerge = (tableIds) =>
  post('/ops/tables/merge-preview', { table_ids: tableIds })

export const bookTable = async (tableId, payload = {}) => {
  try {
    const data = await api.post(`/ops/tables/${tableId}/book`, payload, { params: _params() }).then(r => r.data)
    invalidateCacheByPrefix('/ops/tables')
    return data
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

export const settleTable = async (tableId, payload = {}) => {
  try {
    const data = await api.post(`/ops/tables/${tableId}/settle`, payload).then(r => r.data)
    invalidateCacheByPrefix('/ops/tables')
    return data
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

export const reserveTable = async (tableId) => {
  try {
    const data = await api.post(`/ops/tables/${tableId}/reserve`).then(r => r.data)
    invalidateCacheByPrefix('/ops/tables')
    return data
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

export const unreserveTable = async (tableId) => {
  try {
    const data = await api.post(`/ops/tables/${tableId}/unreserve`).then(r => r.data)
    invalidateCacheByPrefix('/ops/tables')
    return data
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

export const seatReservedTable = async (tableId) => {
  try {
    const data = await api.post(`/ops/tables/${tableId}/seat`, {}, { params: _params() }).then(r => r.data)
    invalidateCacheByPrefix('/ops/tables')
    return data
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

export const getMenuItemsList = (search = '') =>
  api.get('/ops/menu-items', { params: _params({ search: search || undefined }) }).then(r => r.data)

export const addItemToTableOrder = async (tableId, itemId, quantity = 1) => {
  try {
    const data = await api.post(`/ops/tables/${tableId}/add-item`, null, { params: { item_id: itemId, quantity } }).then(r => r.data)
    invalidateCacheByPrefix('/ops/tables')
    return data
  } catch (error) {
    console.error('API Error:', error?.response?.data || error.message)
    throw normalizeError(error)
  }
}

export const adjustInventory = (payload) =>
  post('/ops/inventory/adjust', payload).then((data) => {
    invalidateCacheByPrefix('/ops/inventory?')
    return data
  })

export const updateIngredient = (ingredientId, payload) =>
  patch(`/ops/inventory/${ingredientId}`, payload).then((data) => {
    invalidateCacheByPrefix('/ops/inventory?')
    return data
  })

export const exportReportsCsv = (params = {}) =>
  api.get('/ops/reports/export', { params, responseType: 'blob' }).then((r) => r.data)

export default api
