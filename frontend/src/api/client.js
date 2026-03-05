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

export const getCombos = () =>
  api.get('/revenue/combos').then(r => r.data)

export const getPriceRecommendations = () =>
  api.get('/revenue/price-recommendations').then(r => r.data)

export const getCategoryBreakdown = () =>
  api.get('/revenue/category-breakdown').then(r => r.data)

// ── Voice Ordering ──

export const transcribeAudio = (audioBlob) => {
  const form = new FormData()
  form.append('file', audioBlob, 'recording.webm')
  return api.post('/voice/transcribe', form).then(r => r.data)
}

export const processVoiceAudio = (audioBlob) => {
  const form = new FormData()
  form.append('file', audioBlob, 'recording.webm')
  return api.post('/voice/process-audio', form).then(r => r.data)
}

export const processVoiceText = (text) =>
  api.post('/voice/process', { text }).then(r => r.data)

export const confirmOrder = (orderData) =>
  api.post('/voice/confirm-order', orderData).then(r => r.data)

export const getVoiceOrders = () =>
  api.get('/voice/orders').then(r => r.data)

export default api
