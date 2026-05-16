import { useState, useEffect } from 'react'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ZAxis } from 'recharts'
import { Users, AlertTriangle, TrendingDown, Shield } from 'lucide-react'
import { suppliersAPI } from '../api/client'
import { StatCard } from '../components/StatCard'
import { RiskBadge } from '../components/RiskBadge'

function ReliabilityBar({ value, color = '#0ea5e9' }) {
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

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs">
        <div className="font-semibold text-slate-100 mb-1">{d.name}</div>
        <div className="text-slate-400">OTD: {(d.x * 100).toFixed(0)}%</div>
        <div className="text-slate-400">Reliability: {(d.y * 100).toFixed(0)}%</div>
        <div className="text-slate-400">Single Source Parts: {d.z}</div>
      </div>
    )
  }
  return null
}

export default function SupplierRisk() {
  const [suppliers, setSuppliers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    suppliersAPI.getRiskMap()
      .then(res => setSuppliers(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const highRisk = suppliers.filter(s => s.reliability_score < 0.8 || s.on_time_delivery_rate < 0.8).length
  const singleSource = suppliers.reduce((sum, s) => sum + s.single_source_parts_count, 0)
  const delayedTotal = suppliers.reduce((sum, s) => sum + s.delayed_pos, 0)

  const scatterData = suppliers.map(s => ({
    x: s.on_time_delivery_rate,
    y: s.reliability_score,
    z: Math.max(50, s.single_source_parts_count * 40 + 50),
    name: s.name,
    risk: s.risk_score,
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
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Supplier Risk Map</h1>
        <p className="text-slate-400 text-sm mt-1">Supplier reliability, delivery performance, and single-source exposure</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard icon={AlertTriangle} value={highRisk} label="High-Risk Suppliers" color="red" critical={highRisk > 0} />
        <StatCard icon={Shield} value={singleSource} label="Single-Source Parts at Risk" color="orange" />
        <StatCard icon={TrendingDown} value={delayedTotal} label="Delayed Purchase Orders" color="yellow" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Scatter chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-slate-100 mb-1">OTD Rate vs Reliability Score</h2>
          <p className="text-xs text-slate-500 mb-4">Bubble size = single-source parts count. Bottom-left = highest risk.</p>
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
                fill="#0ea5e9"
                fillOpacity={0.7}
                shape={(props) => {
                  const { cx, cy, payload } = props
                  const color = payload.risk >= 80 ? '#ef4444' : payload.risk >= 60 ? '#f97316' : '#0ea5e9'
                  const r = Math.sqrt(payload.z / Math.PI)
                  return <circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.6} stroke={color} strokeWidth={1} />
                }}
              />
            </ScatterChart>
          </ResponsiveContainer>
          {/* Legend */}
          <div className="flex gap-4 mt-2 text-xs text-slate-500">
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-red-500/60" />Critical Risk</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-orange-500/60" />High Risk</div>
            <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-sky-500/60" />Acceptable</div>
          </div>
        </div>

        {/* Supplier table */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-gray-800">
            <h2 className="font-semibold text-slate-100">Supplier Risk Ranking</h2>
          </div>
          <div className="divide-y divide-gray-800">
            {suppliers.map(s => (
              <div
                key={s.id}
                className={`p-4 hover:bg-gray-800/30 transition-colors ${
                  (s.reliability_score < 0.8 || s.on_time_delivery_rate < 0.8) ? 'border-l-2 border-l-orange-500' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-slate-200 text-sm truncate">{s.name}</span>
                      {(s.reliability_score < 0.8 || s.on_time_delivery_rate < 0.8) && (
                        <AlertTriangle size={12} className="text-orange-400 shrink-0" />
                      )}
                    </div>
                    <div className="text-xs text-slate-500 mb-2">{s.country} · {s.parts_count} parts · {s.single_source_parts_count} single-source</div>
                    <div className="space-y-1">
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
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
