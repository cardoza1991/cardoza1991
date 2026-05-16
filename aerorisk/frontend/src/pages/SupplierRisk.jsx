import { useState, useEffect, useCallback } from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ZAxis } from 'recharts'
import { Users, AlertTriangle, TrendingDown, Shield, RefreshCw, Radio, ShieldAlert, Bug, FileWarning } from 'lucide-react'
import { suppliersAPI, intelAPI } from '../api/client'
import { StatCard } from '../components/StatCard'
import { RiskBadge } from '../components/RiskBadge'

function ReliabilityBar({ value }) {
  const pct = Math.round(value * 100)
  const barColor = pct >= 90 ? '#10b981' : pct >= 80 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: barColor }} />
      </div>
      <span className="text-xs mono text-slate-400 w-8 text-right">{pct}%</span>
    </div>
  )
}

const SIGNAL_ICON = {
  SANCTION: ShieldAlert,
  CVE: Bug,
  ADVISORY: FileWarning,
  CYBER_INCIDENT: Bug,
  NEWS: Radio,
}

const SEVERITY_STYLES = {
  CRITICAL: 'bg-red-500/15 text-red-300 border-red-500/40',
  HIGH:     'bg-orange-500/15 text-orange-300 border-orange-500/40',
  MEDIUM:   'bg-yellow-500/15 text-yellow-300 border-yellow-500/40',
  LOW:      'bg-sky-500/15 text-sky-300 border-sky-500/40',
}

function SeverityBadge({ severity }) {
  return (
    <span className={`text-[10px] px-1.5 py-0.5 border rounded font-semibold tracking-wide ${SEVERITY_STYLES[severity] || SEVERITY_STYLES.LOW}`}>
      {severity}
    </span>
  )
}

function IntelBadges({ counts }) {
  if (!counts) return null
  const entries = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    .map(k => [k, counts[k] || 0])
    .filter(([, v]) => v > 0)
  if (entries.length === 0) return <span className="text-xs text-slate-600">no signals</span>
  return (
    <div className="flex gap-1 flex-wrap">
      {entries.map(([sev, n]) => (
        <span key={sev} className={`text-[10px] px-1.5 py-0.5 border rounded font-semibold ${SEVERITY_STYLES[sev]}`}>
          {n}&nbsp;{sev[0]}
        </span>
      ))}
    </div>
  )
}

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs">
        <div className="font-semibold text-slate-100 mb-1">{d.name}</div>
        <div className="text-slate-400">OTD: {(d.x * 100).toFixed(0)}%</div>
        <div className="text-slate-400">Reliability: {(d.y * 100).toFixed(0)}%</div>
        <div className="text-slate-400">Single Source Parts: {d.ssCount}</div>
        {d.intel > 0 && <div className="text-red-400">Active intel signals: {d.intel}</div>}
      </div>
    )
  }
  return null
}

function SignalRow({ signal }) {
  const Icon = SIGNAL_ICON[signal.signal_type] || Radio
  const observed = signal.observed_at ? signal.observed_at.split('T')[0] : ''
  return (
    <div className="flex gap-2 items-start p-2 hover:bg-gray-800/40 rounded">
      <Icon size={14} className="text-slate-400 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <SeverityBadge severity={signal.severity} />
          <span className="text-[10px] mono text-slate-500">{signal.source}</span>
          {signal.supplier_name && (
            <span className="text-[10px] text-slate-400 truncate">→ {signal.supplier_name}</span>
          )}
          <span className="text-[10px] text-slate-600 ml-auto shrink-0">{observed}</span>
        </div>
        <div className="text-xs text-slate-300 truncate" title={signal.title}>{signal.title}</div>
        {signal.body && (
          <div className="text-[11px] text-slate-500 line-clamp-2 mt-0.5">{signal.body}</div>
        )}
      </div>
    </div>
  )
}

export default function SupplierRisk() {
  const [suppliers, setSuppliers] = useState([])
  const [signals, setSignals] = useState([])
  const [intelSummary, setIntelSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [expanded, setExpanded] = useState(null)

  const load = useCallback(() => {
    return Promise.all([
      suppliersAPI.getRiskMap().then(r => setSuppliers(r.data)),
      intelAPI.getSignals({ limit: 25, active_only: true }).then(r => setSignals(r.data)),
      intelAPI.getSummary().then(r => setIntelSummary(r.data)),
    ])
  }, [])

  useEffect(() => {
    load().catch(console.error).finally(() => setLoading(false))
  }, [load])

  const refresh = async () => {
    setRefreshing(true)
    try {
      await intelAPI.refresh()
      await load()
    } catch (e) { console.error(e) } finally { setRefreshing(false) }
  }

  const highRisk = suppliers.filter(s => s.reliability_score < 0.8 || s.on_time_delivery_rate < 0.8).length
  const singleSource = suppliers.reduce((sum, s) => sum + s.single_source_parts_count, 0)
  const delayedTotal = suppliers.reduce((sum, s) => sum + s.delayed_pos, 0)

  const scatterData = suppliers.map(s => ({
    x: s.on_time_delivery_rate,
    y: s.reliability_score,
    z: Math.max(50, s.single_source_parts_count * 40 + 50),
    name: s.name,
    risk: s.risk_score,
    intel: s.intel_signal_count || 0,
    ssCount: s.single_source_parts_count,
  }))

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading supplier data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Supplier Risk Map</h1>
          <p className="text-slate-400 text-sm mt-1">Reliability, delivery performance, single-source exposure, and live external intel</p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-1.5 text-xs bg-sky-500/10 hover:bg-sky-500/20 disabled:opacity-50 border border-sky-500/30 text-sky-300 rounded transition"
        >
          <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Pulling intel…' : 'Refresh intel feeds'}
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={AlertTriangle} value={highRisk} label="High-Risk Suppliers" color="red" critical={highRisk > 0} />
        <StatCard icon={Shield} value={singleSource} label="Single-Source Parts" color="orange" />
        <StatCard icon={TrendingDown} value={delayedTotal} label="Delayed POs" color="yellow" />
        <StatCard
          icon={ShieldAlert}
          value={intelSummary ? intelSummary.critical + intelSummary.high : 0}
          label="Active CRIT+HIGH Intel"
          color="red"
          critical={(intelSummary?.critical || 0) > 0}
        />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Scatter chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-slate-100 mb-1">OTD Rate vs Reliability Score</h2>
          <p className="text-xs text-slate-500 mb-4">Bubble size = single-source parts. Color includes external intel contribution.</p>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                type="number" dataKey="x" name="OTD Rate"
                domain={[0.4, 1.05]} tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                label={{ value: 'On-Time Delivery Rate', position: 'insideBottom', fill: '#6b7280', fontSize: 11, dy: 10 }}
              />
              <YAxis
                type="number" dataKey="y" name="Reliability"
                domain={[0.5, 1.05]} tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                label={{ value: 'Reliability Score', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11, dx: -5 }}
              />
              <ZAxis type="number" dataKey="z" range={[40, 200]} />
              <Tooltip content={<CustomTooltip />} />
              <Scatter
                data={scatterData}
                shape={(props) => {
                  const { cx, cy, payload } = props
                  const color = payload.risk >= 80 ? '#ef4444' : payload.risk >= 60 ? '#f97316' : '#0ea5e9'
                  const r = Math.sqrt(payload.z / Math.PI)
                  return (
                    <g>
                      <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.6} stroke={color} strokeWidth={1} />
                      {payload.intel > 0 && (
                        <circle cx={cx} cy={cy} r={r + 3} fill="none" stroke="#ef4444" strokeWidth={1.5} strokeDasharray="3 2" />
                      )}
                    </g>
                  )
                }}
              />
            </ScatterChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 text-xs text-slate-500 flex-wrap">
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-red-500/60" />Critical Risk</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-orange-500/60" />High Risk</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-sky-500/60" />Acceptable</div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full border border-dashed border-red-500" />Active intel
            </div>
          </div>
        </div>

        {/* Live intel feed */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
          <div className="p-5 border-b border-gray-800 flex items-center gap-2">
            <Radio size={14} className="text-sky-400" />
            <h2 className="font-semibold text-slate-100">Live Intel Feed</h2>
            <span className="text-xs text-slate-500 ml-2">{signals.length} recent · OFAC · CISA KEV · CISA ICS</span>
          </div>
          <div className="flex-1 overflow-y-auto max-h-[320px] divide-y divide-gray-800/60">
            {signals.length === 0 ? (
              <div className="p-6 text-center text-sm text-slate-500">
                No active intel signals. Click <span className="text-sky-400">Refresh intel feeds</span> above to pull.
              </div>
            ) : (
              signals.map(s => <SignalRow key={s.id} signal={s} />)
            )}
          </div>
        </div>
      </div>

      {/* Supplier table — full width */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-gray-800">
          <h2 className="font-semibold text-slate-100">Supplier Risk Ranking</h2>
          <p className="text-xs text-slate-500 mt-1">Score combines OTD, reliability, defect rate, single-source exposure, delayed POs, and active intel signals.</p>
        </div>
        <div className="divide-y divide-gray-800">
          {suppliers.map(s => {
            const isOpen = expanded === s.id
            const hasIntel = (s.intel_signal_count || 0) > 0
            return (
              <div key={s.id}>
                <button
                  onClick={() => setExpanded(isOpen ? null : s.id)}
                  className={`w-full text-left p-4 hover:bg-gray-800/30 transition-colors ${
                    hasIntel ? 'border-l-2 border-l-red-500' :
                    (s.reliability_score < 0.8 || s.on_time_delivery_rate < 0.8) ? 'border-l-2 border-l-orange-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-medium text-slate-200 text-sm truncate">{s.name}</span>
                        {hasIntel && <ShieldAlert size={12} className="text-red-400 shrink-0" />}
                        <IntelBadges counts={s.intel_by_severity} />
                      </div>
                      <div className="text-xs text-slate-500 mb-2">
                        {s.country} · {s.parts_count} parts · {s.single_source_parts_count} single-source
                        {s.intel_contribution > 0 && (
                          <span className="text-red-400"> · +{s.intel_contribution} pts from intel</span>
                        )}
                      </div>
                      <div className="space-y-1 max-w-md">
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-slate-500 w-16 shrink-0">OTD Rate</span>
                          <ReliabilityBar value={s.on_time_delivery_rate} />
                        </div>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-slate-500 w-16 shrink-0">Reliability</span>
                          <ReliabilityBar value={s.reliability_score} />
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <RiskBadge score={s.risk_score} />
                      <div className="text-xs text-slate-500 mt-1">
                        {s.open_pos} open PO{s.open_pos !== 1 ? 's' : ''}
                        {s.delayed_pos > 0 && <span className="text-red-400"> · {s.delayed_pos} delayed</span>}
                      </div>
                      <div className="text-xs text-slate-500">Defect: {(s.defect_rate * 100).toFixed(1)}%</div>
                    </div>
                  </div>
                </button>

                {isOpen && (
                  <div className="bg-gray-950/60 border-t border-gray-800 p-4 space-y-2">
                    {s.explanation && (
                      <div className="text-xs text-slate-400 mb-2 leading-relaxed">{s.explanation}</div>
                    )}
                    {(s.intel_signals || []).length === 0 ? (
                      <div className="text-xs text-slate-500 italic">No active intel signals for this supplier.</div>
                    ) : (
                      <div className="divide-y divide-gray-800/60">
                        {s.intel_signals.map(sig => (
                          <SignalRow key={sig.id} signal={{ ...sig, supplier_name: null }} />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
