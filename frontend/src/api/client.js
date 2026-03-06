import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api', // Pointing to localhost:8000 as per spec
  timeout: 30000,
})

// Add a response interceptor for uniform error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    // Return a uniform error shape or throw
    return Promise.reject(error.response?.data || { detail: 'An unknown API error occurred.' })
  }
)

// ── Revenue Intelligence ──

export const getDashboardMetrics = () =>
  api.get('/revenue/dashboard').then(r => r.data)

export const getMenuMatrix = () =>
  api.get('/revenue/menu-matrix').then(r => r.data)

export const getHiddenStars = () =>
  api.get('/revenue/hidden-stars').then(r => r.data)

export const getRisks = () =>
  api.get('/revenue/risks').then(r => r.data)

export const getCombos = (forceRetrain = false, discountPct = 10) =>
  api.get('/revenue/combos', { params: { force_retrain: forceRetrain, discount_pct: discountPct } }).then(r => r.data)

export const getPriceRecommendations = () =>
  api.get('/revenue/price-recommendations').then(r => r.data)

export const getCategoryBreakdown = () =>
  api.get('/revenue/category-breakdown').then(r => r.data)

// ── Trends & Time-Series ──

export const getTrends = () =>
  api.get('/revenue/trends').then(r => r.data)

export const getWowMom = () =>
  api.get('/revenue/trends/wow-mom').then(r => r.data)

export const getPriceElasticity = () =>
  api.get('/revenue/trends/price-elasticity').then(r => r.data)

// ── Advanced Analytics ──

export const getCannibalization = (days = 90) =>
  api.get('/revenue/analytics/cannibalization', { params: { days } }).then(r => r.data)

export const getPriceSensitivity = () =>
  api.get('/revenue/analytics/price-sensitivity').then(r => r.data)

export const getWasteAnalysis = (days = 30) =>
  api.get('/revenue/analytics/waste', { params: { days } }).then(r => r.data)

export const getCustomerReturns = (days = 30) =>
  api.get('/revenue/analytics/customer-returns', { params: { days } }).then(r => r.data)

export const getMenuComplexity = () =>
  api.get('/revenue/analytics/menu-complexity').then(r => r.data)

export const getOperationalMetrics = (days = 30) =>
  api.get('/revenue/analytics/operational', { params: { days } }).then(r => r.data)

// ── Voice Ordering ──

export const transcribeAudio = (audioBlob, sessionId) => {
  const form = new FormData()
  if (audioBlob) {
    form.append('audio', audioBlob, 'recording.webm')
  }
  if (sessionId) {
    form.append('session_id', sessionId)
  }
  return api.post('/voice/process-audio', form).then(r => r.data)
}

export const submitTextOrder = (text, sessionId) =>
  api.post('/voice/process', { text, session_id: sessionId || null })
    .then(r => r.data)

export const confirmOrder = (order, kot) =>
  api.post('/voice/confirm-order', { order, kot }).then(r => r.data)

// ── Health ──

export const getVoiceOrders = () =>
  api.get('/voice/orders').then(r => r.data)

// —— Operations ——

export const getOpsOrders = (params = {}) =>
  api.get('/ops/orders', { params }).then(r => r.data)

export const getOpsTables = () =>
  api.get('/ops/tables').then(r => r.data)

export const getOpsTablesFiltered = (params = {}) =>
  api.get('/ops/tables', { params }).then(r => r.data)

export const getOpsInventory = (days = 30) =>
  api.get('/ops/inventory', { params: { days } }).then(r => r.data)

export const getOpsInventoryFiltered = (params = {}) =>
  api.get('/ops/inventory', { params }).then(r => r.data)

export const getOpsReports = (days = 14) =>
  api.get('/ops/reports', { params: { days } }).then(r => r.data)

export const getOpsReportsFiltered = (params = {}) =>
  api.get('/ops/reports', { params }).then(r => r.data)

export const getOpsSettings = () =>
  api.get('/ops/settings').then(r => r.data)

export const updateTableStatus = (tableId, payload) =>
  api.patch(`/ops/tables/${tableId}`, payload).then(r => r.data)

export const adjustInventory = (payload) =>
  api.post('/ops/inventory/adjust', payload).then(r => r.data)

export const updateIngredient = (ingredientId, payload) =>
  api.patch(`/ops/inventory/${ingredientId}`, payload).then(r => r.data)

export const exportReportsCsv = (params = {}) =>
  api.get('/ops/reports/export', { params, responseType: 'blob' }).then(r => r.data)

export default api
