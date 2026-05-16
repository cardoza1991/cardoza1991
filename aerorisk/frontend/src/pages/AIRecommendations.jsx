import { useState, useEffect } from 'react'
import { AlertTriangle, ChevronDown, ChevronRight, RefreshCw, Zap, Check } from 'lucide-react'
import { agentAPI } from '../api/client'
import { AlertBanner } from '../components/AlertBanner'
import { RiskBadge } from '../components/RiskBadge'

const PRIORITY_CLASSES = {
  CRITICAL: 'border-red-500/40 bg-red-950/10',
  HIGH: 'border-orange-500/30 bg-orange-950/10',
  MEDIUM: 'border-yellow-500/30 bg-yellow-950/10',
  LOW: 'border-gray-700',
}

const TYPE_LABELS = {
  EXPEDITE_ORDER: 'Expedite Order',
  FIND_ALT_SUPPLIER: 'Find Alt. Supplier',
  RESCHEDULE_MAINTENANCE: 'Reschedule Maint.',
  ALERT: 'Alert',
}

function RecommendationCard({ rec, onStatusChange }) {
  const [expanded, setExpanded] = useState(rec.priority === 'CRITICAL')

  return (
    <div className={`rounded-xl border ${PRIORITY_CLASSES[rec.priority] || 'border-gray-700'} overflow-hidden`}>
      <div
        className="flex items-start gap-4 p-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="shrink-0 mt-0.5">
          <RiskBadge level={rec.priority} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              <div className="text-sm font-semibold text-slate-100 leading-snug mb-1">{rec.title}</div>
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="bg-gray-800 px-2 py-0.5 rounded">{TYPE_LABELS[rec.recommendation_type] || rec.recommendation_type}</span>
                {rec.aircraft_affected && <span className="mono text-sky-400">{rec.aircraft_affected}</span>}
                {rec.part_affected && <span className="mono text-slate-400">{rec.part_affected}</span>}
                {rec.supplier_affected && <span className="text-slate-400">{rec.supplier_affected}</span>}
                <span className="text-slate-600">{rec.created_at ? new Date(rec.created_at).toLocaleDateString() : ''}</span>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className={`text-xs px-2 py-0.5 rounded mono ${
                rec.status === 'OPEN' ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20' :
                rec.status === 'IN_PROGRESS' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                rec.status === 'RESOLVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                'bg-gray-700 text-slate-400'
              }`}>{rec.status}</span>
              {expanded ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
            </div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-800/50 px-4 py-4 space-y-3">
          <div>
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Description</div>
            <div className="text-sm text-slate-300 leading-relaxed">{rec.description}</div>
          </div>
          {rec.rationale && (
            <div>
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Rationale</div>
              <div className="text-sm text-slate-400 leading-relaxed">{rec.rationale}</div>
            </div>
          )}
          {rec.estimated_impact && (
            <div>
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Estimated Impact</div>
              <div className="text-sm text-orange-300/80 leading-relaxed">{rec.estimated_impact}</div>
            </div>
          )}
          {rec.action_steps && rec.action_steps.length > 0 && (
            <div>
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Action Steps</div>
              <ol className="space-y-1.5">
                {rec.action_steps.map((step, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="shrink-0 w-5 h-5 rounded bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs flex items-center justify-center font-medium">{i + 1}</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AIRecommendations() {
  const [recommendations, setRecommendations] = useState([])
  const [alerts, setAlerts] = useState([])
  const [filter, setFilter] = useState('ALL')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const loadData = () => {
    setLoading(true)
    Promise.all([agentAPI.getRecommendations(), agentAPI.getAlerts()])
      .then(([recRes, alertRes]) => {
        setRecommendations(recRes.data)
        setAlerts(alertRes.data)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(loadData, [])

  const handleRunCycle = async () => {
    setRunning(true)
    try {
      await agentAPI.runCycle()
      loadData()
    } catch(e) {
      console.error(e)
    } finally {
      setRunning(false)
    }
  }

  const filtered = recommendations.filter(r => {
    if (filter === 'ALL') return true
    if (filter === 'OPEN') return r.status === 'OPEN'
    return r.priority === filter
  })

  const tabs = [
    { key: 'ALL', label: 'All', count: recommendations.length },
    { key: 'CRITICAL', label: 'Critical', count: recommendations.filter(r => r.priority === 'CRITICAL').length },
    { key: 'HIGH', label: 'High', count: recommendations.filter(r => r.priority === 'HIGH').length },
    { key: 'OPEN', label: 'Open', count: recommendations.filter(r => r.status === 'OPEN').length },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading recommendations...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">AI Recommendations</h1>
          <p className="text-slate-400 text-sm mt-1">Autonomous agent analysis and mitigation actions</p>
        </div>
        <button
          onClick={handleRunCycle}
          disabled={running}
          className="flex items-center gap-2 px-4 py-2 bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 text-sky-400 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
        >
          {running ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
          Run Agent Cycle
        </button>
      </div>

      <AlertBanner alerts={alerts} />

      {/* Filter tabs */}
      <div className="flex items-center gap-2">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setFilter(t.key)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              filter === t.key
                ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                : 'text-slate-400 hover:text-slate-200 border border-transparent'
            }`}
          >
            {t.label}
            {t.count > 0 && (
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                filter === t.key ? 'bg-sky-500/20 text-sky-400' : 'bg-gray-700 text-slate-400'
              }`}>{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Recommendations */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="text-slate-500 text-center py-12">No recommendations for this filter</div>
        ) : (
          filtered.map(rec => (
            <RecommendationCard key={rec.id} rec={rec} />
          ))
        )}
      </div>
    </div>
  )
}
