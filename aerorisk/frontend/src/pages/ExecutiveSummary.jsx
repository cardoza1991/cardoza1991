import { useState, useEffect, useRef } from 'react'
import { riskAPI, agentAPI } from '../api/client'
import { FileText, Zap, AlertTriangle, CheckCircle, Clock, Target, Activity, Send } from 'lucide-react'
import { RiskBadge } from '../components/RiskBadge'

const DEFAULT_QUERY = "Show me which aircraft are at risk of becoming non-mission-capable in the next 30 days due to supply chain issues, explain why, and recommend mitigation actions."

function ReadinessGauge({ percentage }) {
  const radius = 70
  const stroke = 10
  const normalizedRadius = radius - stroke / 2
  const circumference = normalizedRadius * 2 * Math.PI
  const strokeDashoffset = circumference - (percentage / 100) * circumference
  const color = percentage >= 80 ? '#10b981' : percentage >= 60 ? '#f59e0b' : '#ef4444'

  return (
    <div className="flex flex-col items-center">
      <svg height={radius * 2 + 10} width={radius * 2 + 10}>
        <circle
          stroke="#1f2937"
          fill="transparent"
          strokeWidth={stroke}
          r={normalizedRadius}
          cx={radius + 5}
          cy={radius + 5}
        />
        <circle
          stroke={color}
          fill="transparent"
          strokeWidth={stroke}
          strokeDasharray={`${circumference} ${circumference}`}
          style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.5s ease', transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
          r={normalizedRadius}
          cx={radius + 5}
          cy={radius + 5}
          strokeLinecap="round"
        />
        <text x={radius + 5} y={radius + 5} textAnchor="middle" dy="0.3em" style={{ fill: color, fontSize: 22, fontWeight: 700 }}>
          {Math.round(percentage)}%
        </text>
      </svg>
      <div className="text-xs text-slate-400 mt-1">MISSION READINESS</div>
    </div>
  )
}

function NMCCard({ aircraft }) {
  const statusColors = {
    NMC: 'border-red-500/50 bg-red-950/20',
    AT_RISK: 'border-orange-500/40 bg-orange-950/10',
    PMC: 'border-yellow-500/30 bg-yellow-950/10',
  }

  return (
    <div className={`rounded-xl border p-4 ${statusColors[aircraft.current_status] || 'border-gray-800'}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="mono font-bold text-sky-400">{aircraft.tail_number}</span>
            <span className="text-sm text-slate-400">{aircraft.platform}</span>
          </div>
          <div className="text-xs text-slate-500 mt-0.5">{aircraft.squadron}</div>
        </div>
        <div className="text-right">
          <RiskBadge score={aircraft.risk_score} />
          <div className={`text-xs mt-1 font-semibold ${aircraft.days_to_nmc === 0 ? 'text-red-400' : aircraft.days_to_nmc <= 7 ? 'text-red-400' : 'text-orange-400'}`}>
            {aircraft.days_to_nmc === 0 ? 'NMC NOW' : `NMC in ~${aircraft.days_to_nmc}d`}
          </div>
        </div>
      </div>

      <div className="text-xs text-slate-400 leading-relaxed mb-3 line-clamp-3">{aircraft.root_cause}</div>

      <div className="grid grid-cols-2 gap-2 text-xs mb-3">
        {aircraft.blocking_part && (
          <div>
            <span className="text-slate-500">Blocking Part</span>
            <div className="mono text-red-400">{aircraft.blocking_part}</div>
          </div>
        )}
        {aircraft.supplier && (
          <div>
            <span className="text-slate-500">Supplier</span>
            <div className="text-slate-300">{aircraft.supplier}</div>
          </div>
        )}
        {aircraft.po_status && (
          <div>
            <span className="text-slate-500">PO Status</span>
            <div className={`font-medium ${aircraft.po_status.includes('DELAY') ? 'text-red-400' : 'text-sky-400'}`}>{aircraft.po_status}</div>
          </div>
        )}
      </div>

      {aircraft.mitigation && aircraft.mitigation.length > 0 && (
        <div>
          <div className="text-xs font-medium text-slate-400 mb-1">Top Mitigation</div>
          <div className="text-xs text-emerald-400/80 bg-emerald-500/5 border border-emerald-500/10 rounded px-2 py-1.5 leading-relaxed">
            {aircraft.mitigation[0]}
          </div>
        </div>
      )}
    </div>
  )
}

export default function ExecutiveSummary() {
  const [forecast, setForecast] = useState(null)
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState(DEFAULT_QUERY)
  const [queryResult, setQueryResult] = useState(null)
  const [querying, setQuerying] = useState(false)
  const resultRef = useRef(null)

  useEffect(() => {
    Promise.all([riskAPI.getNMCForecast(), agentAPI.getSummary()])
      .then(([forecastRes, summaryRes]) => {
        setForecast(forecastRes.data)
        setSummary(summaryRes.data.summary || '')
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleQuery = async () => {
    if (!query.trim()) return
    setQuerying(true)
    try {
      const { data } = await agentAPI.runQuery(query)
      setQueryResult(data)
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch (e) {
      console.error(e)
    } finally {
      setQuerying(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleQuery()
  }

  const readinessPct = forecast?.aircraft
    ? 100 - (forecast.at_risk_count / Math.max(1, 12) * 100)
    : 75

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading executive data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 text-sky-400 text-xs font-medium uppercase tracking-widest mb-1">
            <Activity size={14} />
            Commander's Brief
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Executive Summary</h1>
          <p className="text-slate-400 text-sm mt-1">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 bg-gray-900 border border-gray-800 rounded-lg px-3 py-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          LIVE INTELLIGENCE
        </div>
      </div>

      {/* Top row */}
      <div className="grid grid-cols-3 gap-6">
        {/* Gauge */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col items-center justify-center">
          <ReadinessGauge percentage={readinessPct} />
          <div className="grid grid-cols-2 gap-2 mt-4 w-full text-xs">
            <div className="text-center">
              <div className="text-lg font-bold text-emerald-400">
                {forecast?.aircraft ? 12 - forecast.at_risk_count : '—'}
              </div>
              <div className="text-slate-500">Available</div>
            </div>
            <div className="text-center">
              <div className={`text-lg font-bold ${(forecast?.at_risk_count ?? 0) > 0 ? 'text-red-400' : 'text-slate-400'}`}>
                {forecast?.at_risk_count ?? '—'}
              </div>
              <div className="text-slate-500">At Risk</div>
            </div>
          </div>
        </div>

        {/* Leadership summary */}
        <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={16} className="text-sky-400" />
            <h2 className="font-semibold text-slate-100">AI Intelligence Summary</h2>
          </div>
          <pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap overflow-auto max-h-52 leading-relaxed">
            {summary || 'No summary available. Run agent cycle to generate.'}
          </pre>
        </div>
      </div>

      {/* NMC Forecast */}
      {forecast && forecast.aircraft && forecast.aircraft.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={16} className="text-orange-400" />
            <h2 className="font-semibold text-slate-100">
              NMC Risk Aircraft — Next 30 Days
              <span className="ml-2 text-sm font-normal text-slate-500">({forecast.at_risk_count} aircraft at risk)</span>
            </h2>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {forecast.aircraft.map(ac => (
              <NMCCard key={ac.tail_number} aircraft={ac} />
            ))}
          </div>
        </div>
      )}

      {/* Money Shot — AI Query */}
      <div className="bg-gray-900 border border-sky-500/20 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-gray-800 bg-sky-500/5">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-sky-500/15 rounded-lg">
              <Zap size={16} className="text-sky-400" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-100">AeroRisk AI Intelligence Query</h2>
              <p className="text-xs text-slate-400 mt-0.5">Ask any supply chain risk question — powered by autonomous agent analysis</p>
            </div>
          </div>
        </div>
        <div className="p-5 space-y-3">
          <div className="relative">
            <textarea
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
              className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-3 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-sky-500/50 resize-none transition-colors"
              placeholder="Ask a supply chain risk question..."
            />
            <div className="text-xs text-slate-600 mt-1">Ctrl+Enter to submit</div>
          </div>
          <button
            onClick={handleQuery}
            disabled={querying || !query.trim()}
            className="flex items-center gap-2 px-5 py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-sky-900/40 disabled:text-sky-700 text-white rounded-lg text-sm font-medium transition-all"
          >
            {querying ? (
              <>
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Send size={14} />
                Ask AeroRisk AI
              </>
            )}
          </button>
        </div>
      </div>

      {/* Query result */}
      {queryResult && (
        <div ref={resultRef} className="bg-gray-950 border border-gray-700 rounded-xl overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-800 bg-gray-900">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-medium text-emerald-400">AeroRisk AI Response</span>
            <span className="text-xs text-slate-500 ml-auto">
              Confidence: {(queryResult.response.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="p-5 space-y-4">
            {/* Summary */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-4">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Summary</div>
              <div className="text-sm text-slate-200 leading-relaxed">{queryResult.response.summary}</div>
            </div>

            {/* Fleet Status */}
            {queryResult.response.fleet_status && (
              <div>
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Fleet Status</div>
                <div className="grid grid-cols-5 gap-2">
                  {[
                    { label: 'Total', value: queryResult.response.fleet_status.total, color: 'text-slate-300' },
                    { label: 'FMC', value: queryResult.response.fleet_status.fmc, color: 'text-emerald-400' },
                    { label: 'PMC', value: queryResult.response.fleet_status.pmc, color: 'text-yellow-400' },
                    { label: 'NMC', value: queryResult.response.fleet_status.nmc, color: 'text-red-400' },
                    { label: 'AT RISK', value: queryResult.response.fleet_status.at_risk, color: 'text-orange-400' },
                  ].map(s => (
                    <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
                      <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
                      <div className="text-xs text-slate-500">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* At Risk Aircraft */}
            {queryResult.response.at_risk_aircraft && queryResult.response.at_risk_aircraft.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">At-Risk Aircraft Detail</div>
                <div className="space-y-3">
                  {queryResult.response.at_risk_aircraft.map(ac => (
                    <div key={ac.tail_number} className="bg-gray-900 border border-red-500/20 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="mono font-bold text-sky-400">{ac.tail_number}</span>
                          <span className="text-sm text-slate-400">{ac.platform}</span>
                          <RiskBadge score={ac.risk_score} />
                        </div>
                        <div className={`text-sm font-semibold ${ac.days_to_nmc === 0 ? 'text-red-400' : 'text-orange-400'}`}>
                          {ac.days_to_nmc === 0 ? 'NMC NOW' : `NMC in ~${ac.days_to_nmc}d`}
                        </div>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed mb-3">{ac.root_cause}</p>
                      <div className="flex flex-wrap gap-3 text-xs mb-3">
                        {ac.blocking_part && (
                          <span className="mono text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded">
                            BLOCKING: {ac.blocking_part}
                          </span>
                        )}
                        {ac.supplier && <span className="text-slate-400">Supplier: {ac.supplier}</span>}
                        {ac.po_status && (
                          <span className={`${ac.po_status.includes('DELAY') ? 'text-red-400' : 'text-sky-400'}`}>
                            PO: {ac.po_status}
                          </span>
                        )}
                      </div>
                      {ac.mitigation && ac.mitigation.length > 0 && (
                        <div>
                          <div className="text-xs text-slate-500 mb-1">Mitigation Actions:</div>
                          <ul className="space-y-1">
                            {ac.mitigation.map((m, i) => (
                              <li key={i} className="text-xs text-emerald-400/80 flex items-start gap-1.5">
                                <span className="text-emerald-500 mt-0.5 shrink-0">→</span>
                                {m}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommended Actions */}
            {queryResult.response.recommended_actions && queryResult.response.recommended_actions.length > 0 && (
              <div>
                <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Top Recommended Actions</div>
                <div className="space-y-2">
                  {queryResult.response.recommended_actions.map((action, i) => (
                    <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <RiskBadge level={action.priority} />
                        <span className="text-xs text-slate-300 font-medium">{action.title}</span>
                      </div>
                      {action.actions && action.actions.length > 0 && (
                        <ul className="space-y-0.5">
                          {action.actions.slice(0, 2).map((a, j) => (
                            <li key={j} className="text-xs text-slate-400 flex items-start gap-1.5">
                              <span className="text-sky-500 shrink-0 mt-0.5">•</span>
                              {a}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
