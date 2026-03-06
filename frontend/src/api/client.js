import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
})

const inflightGets = new Map()
const responseCache = new Map()

const SHORT_CACHE_TTL_MS = 20000
const DEFAULT_CACHE_TTL_MS = 45000
const LONG_CACHE_TTL_MS = 120000
const TRANSIENT_STATUS = new Set([408, 425, 429, 500, 502, 503, 504])

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

export const transcribeAudio = (audioBlob, sessionId) => {
  const form = new FormData()
  if (audioBlob) {
    form.append('audio', audioBlob, 'recording.webm')
  }
  if (sessionId) {
    form.append('session_id', sessionId)
  }
  return post('/voice/process-audio', form)
}

export const submitTextOrder = (text, sessionId) =>
  post('/voice/process', { text, session_id: sessionId || null })

export const confirmOrder = (order, kot) =>
  post('/voice/confirm-order', { order, kot })

export const speakText = (text, language = 'en') =>
  post('/voice/speak', { text, language })

export const getVoiceOrders = () =>
  getWithCache('/voice/orders', { ttlMs: SHORT_CACHE_TTL_MS })

export const getOpsOrders = (params = {}) =>
  getWithCache('/ops/orders', { params, ttlMs: SHORT_CACHE_TTL_MS })

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
  getWithCache('/ops/settings', { ttlMs: LONG_CACHE_TTL_MS })

export const updateTableStatus = (tableId, payload) =>
  patch(`/ops/tables/${tableId}`, payload).then((data) => {
    invalidateCacheByPrefix('/ops/tables?')
    return data
  })

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
