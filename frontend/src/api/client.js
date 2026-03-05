/**
 * client.js — API Client
 * All backend API calls in one place.
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ── Revenue Intelligence ──

export const getFullAnalysis = () =>
  api.get('/revenue/analyze').then(r => r.data)

export const getMargins = () =>
  api.get('/revenue/margins').then(r => r.data)

export const getPopularity = () =>
  api.get('/revenue/popularity').then(r => r.data)

export const getMenuMatrix = () =>
  api.get('/revenue/matrix').then(r => r.data)

export const getHiddenStars = () =>
  api.get('/revenue/hidden-stars').then(r => r.data)

export const getCombos = () =>
  api.get('/revenue/combos').then(r => r.data)

export const getPricing = () =>
  api.get('/revenue/pricing').then(r => r.data)

// ── Voice Ordering ──

export const submitVoiceOrder = (audioBlob, sessionId) => {
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

export const getHealth = () =>
  api.get('/health').then(r => r.data)

export default api
