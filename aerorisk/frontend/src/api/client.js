import axios from 'axios'

const TOKEN_KEY = 'aerorisk_token'

// In dev: VITE_API_BASE is unset → falls back to "/api" and Vite's proxy
// forwards to localhost:8000. In a Cloudflare Pages build: set
// VITE_API_BASE=https://api.your-domain.example so the SPA hits your
// Cloudflare Tunnel hostname instead of the Pages origin.
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const api = axios.create({ baseURL: API_BASE })

// Attach JWT on every request (if we have one).
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401, clear the token so the AuthProvider notices and routes to login.
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err?.response?.status === 401 && !err.config?.url?.endsWith('/auth/me')) {
      localStorage.removeItem(TOKEN_KEY)
      // Soft notify the AuthProvider via a custom event — avoids hard-reload.
      window.dispatchEvent(new CustomEvent('aerorisk:auth-expired'))
    }
    return Promise.reject(err)
  },
)

export const landingAPI = {
  stats: () => api.get('/landing/stats'),
}

export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  getToken: () => localStorage.getItem(TOKEN_KEY),
  setToken: (t) => { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY) },
  logout: () => localStorage.removeItem(TOKEN_KEY),
  auditLog: (params = {}) => api.get('/auth/audit-log', { params }),
}

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

export const bomAPI = {
  list: () => api.get('/bom/'),
  get: (id) => api.get(`/bom/${id}`),
  upload: (file, opts = {}) => {
    const form = new FormData()
    form.append('file', file)
    if (opts.name) form.append('name', opts.name)
    if (opts.target_platform) form.append('target_platform', opts.target_platform)
    if (opts.target_tail_number) form.append('target_tail_number', opts.target_tail_number)
    return api.post('/bom/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  remove: (id) => api.delete(`/bom/${id}`),
}

export const scenariosAPI = {
  list: (params = {}) => api.get('/scenarios/', { params }),
  get: (id) => api.get(`/scenarios/${id}`),
  getByShareToken: (token) => api.get(`/scenarios/share/${token}`),
  notificationLog: (params = {}) => api.get('/scenarios/notifications/log', { params }),
}
