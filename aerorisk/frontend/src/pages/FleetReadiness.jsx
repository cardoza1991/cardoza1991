import { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Plane, CheckCircle, AlertTriangle, XCircle, Clock } from 'lucide-react'
import { fleetAPI } from '../api/client'
import { StatCard } from '../components/StatCard'
import { RiskBadge } from '../components/RiskBadge'

const STATUS_COLORS = {
  FMC: '#10b981',
  PMC: '#f59e0b',
  NMC: '#ef4444',
  AT_RISK: '#f97316',
}

const STATUS_LABELS = {
  FMC: 'Fully Mission Capable',
  PMC: 'Partially Mission Capable',
  NMC: 'Non-Mission Capable',
  AT_RISK: 'At Risk',
}

function RiskBar({ score }) {
  const color = score >= 80 ? 'bg-red-500' : score >= 60 ? 'bg-orange-500' : score >= 40 ? 'bg-yellow-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs mono text-slate-400 w-6 text-right">{Math.round(score)}</span>
    </div>
  )
}

function StatusBadge({ status }) {
  const classes = {
    FMC: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
    PMC: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
    NMC: 'bg-red-500/15 text-red-400 border border-red-500/30',
    AT_RISK: 'bg-orange-500/15 text-orange-400 border border-orange-500/30',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold mono ${classes[status] || 'bg-gray-700 text-slate-400'}`}>
      {status}
    </span>
  )
}

export default function FleetReadiness() {
  const [aircraft, setAircraft] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([fleetAPI.getAll(), fleetAPI.getSummary()])
      .then(([aircraftRes, summaryRes]) => {
        setAircraft(aircraftRes.data)
        setSummary(summaryRes.data)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const pieData = summary ? [
    { name: 'FMC', value: summary.fmc, color: STATUS_COLORS.FMC },
    { name: 'PMC', value: summary.pmc, color: STATUS_COLORS.PMC },
    { name: 'NMC', value: summary.nmc, color: STATUS_COLORS.NMC },
    { name: 'AT_RISK', value: summary.at_risk, color: STATUS_COLORS.AT_RISK },
  ].filter(d => d.value > 0) : []

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading fleet data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Fleet Readiness</h1>
        <p className="text-slate-400 text-sm mt-1">Mission status and supply chain risk across all aircraft</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard icon={Plane} value={summary?.total ?? 0} label="Total Aircraft" color="blue" />
        <StatCard icon={CheckCircle} value={summary?.fmc ?? 0} label="Fully Mission Capable" color="green" />
        <StatCard icon={AlertTriangle} value={(summary?.pmc ?? 0)} label="Partially Mission Capable" color="yellow" />
        <StatCard
          icon={XCircle}
          value={(summary?.nmc ?? 0) + (summary?.at_risk ?? 0)}
          label="NMC / At Risk"
          color="red"
          critical={(summary?.nmc ?? 0) + (summary?.at_risk ?? 0) > 0}
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Aircraft Table */}
        <div className="col-span-2 bg-gray-900 border border-gray-800 rounded-xl">
          <div className="p-5 border-b border-gray-800 flex items-center justify-between">
            <h2 className="font-semibold text-slate-100">Aircraft Status</h2>
            <span className="text-xs text-slate-500">{aircraft.length} aircraft</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Tail #</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Platform</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Squadron</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Risk</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Next Maint</th>
                </tr>
              </thead>
              <tbody>
                {aircraft.map(ac => (
                  <tr
                    key={ac.id}
                    className={`border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors ${
                      ['NMC', 'AT_RISK'].includes(ac.mission_status) ? 'border-l-2 border-l-red-500' : ''
                    }`}
                  >
                    <td className="px-5 py-3 mono text-sky-400 font-medium">{ac.tail_number}</td>
                    <td className="px-4 py-3 text-slate-300">{ac.platform}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{ac.squadron}</td>
                    <td className="px-4 py-3"><StatusBadge status={ac.mission_status} /></td>
                    <td className="px-4 py-3 w-32"><RiskBar score={ac.risk_score} /></td>
                    <td className="px-4 py-3 text-slate-400 text-xs">
                      {ac.days_to_next_maintenance !== null && ac.days_to_next_maintenance !== undefined ? (
                        <span className={`flex items-center gap-1 ${ac.days_to_next_maintenance <= 14 ? 'text-orange-400' : ''}`}>
                          <Clock size={12} />
                          {ac.days_to_next_maintenance}d
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pie Chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-slate-100 mb-4">Readiness Breakdown</h2>
          {pieData.length > 0 ? (
            <>
              <div className="mb-2 text-center">
                <div className="text-3xl font-bold text-emerald-400">{summary?.readiness_percentage?.toFixed(1)}%</div>
                <div className="text-xs text-slate-400">FMC Rate</div>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value">
                    {pieData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '8px' }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 mt-2">
                {pieData.map(d => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ background: d.color }} />
                      <span className="text-slate-400">{STATUS_LABELS[d.name] || d.name}</span>
                    </div>
                    <span className="font-medium text-slate-300">{d.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-slate-500 text-center py-8">No data</div>
          )}
        </div>
      </div>
    </div>
  )
}
