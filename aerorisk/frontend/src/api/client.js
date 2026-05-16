import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const fleetAPI = {
  getAll: () => api.get('/fleet/'),
  getAtRisk: () => api.get('/fleet/at-risk'),
  getSummary: () => api.get('/fleet/readiness-summary'),
  getDetail: (tail) => api.get(`/fleet/${tail}`),
}

export const partsAPI = {
  getAll: () => api.get('/parts/'),
  getCriticalWatchlist: () => api.get('/parts/critical-watchlist'),
  getStockoutForecast: () => api.get('/parts/stockout-forecast'),
  getDetail: (partNumber) => api.get(`/parts/${partNumber}`),
}

export const suppliersAPI = {
  getAll: () => api.get('/suppliers/'),
  getRiskMap: () => api.get('/suppliers/risk-map'),
  getDetail: (id) => api.get(`/suppliers/${id}`),
}

export const riskAPI = {
  getDashboard: () => api.get('/risk/dashboard'),
  getNMCForecast: () => api.get('/risk/nmc-forecast'),
  recompute: () => api.post('/risk/recompute'),
  getScores: () => api.get('/risk/scores'),
}

export const agentAPI = {
  getRecommendations: () => api.get('/agent/recommendations'),
  getSummary: () => api.get('/agent/summary'),
  getAlerts: () => api.get('/agent/alerts'),
  runQuery: (query) => api.post('/agent/query', { query }),
  runCycle: () => api.post('/agent/run-cycle'),
}

export const intelAPI = {
  getSignals: (params = {}) => api.get('/intel/signals', { params }),
  getSummary: () => api.get('/intel/summary'),
  getFeeds: () => api.get('/intel/feeds'),
  refresh: () => api.post('/intel/refresh'),
  getSupplierIntel: (supplierId) => api.get(`/suppliers/${supplierId}/intel`),
}

export const impactAPI = {
  simulate: (payload) => api.post('/impact/simulate', payload),
  forSupplier: (supplierId, params = {}) => api.get(`/impact/supplier/${supplierId}`, { params }),
  topRisks: (params = {}) => api.get('/impact/top-risks', { params }),
  brief: (params = {}) => api.get('/impact/brief', { params }),
}

export const scenariosAPI = {
  list: (params = {}) => api.get('/scenarios/', { params }),
  get: (id) => api.get(`/scenarios/${id}`),
  getByShareToken: (token) => api.get(`/scenarios/share/${token}`),
  notificationLog: (params = {}) => api.get('/scenarios/notifications/log', { params }),
}
