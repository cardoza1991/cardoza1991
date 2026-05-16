import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import { Package, AlertTriangle, Clock, TrendingDown } from 'lucide-react'
import { partsAPI } from '../api/client'
import { StatCard } from '../components/StatCard'
import { RiskBadge } from '../components/RiskBadge'

function StockBar({ qty, reorder }) {
  const pct = reorder > 0 ? Math.min(100, (qty / (reorder * 3)) * 100) : 50
  const isCritical = qty <= 0
  const isLow = qty <= reorder && qty > 0
  const color = isCritical ? 'bg-red-500' : isLow ? 'bg-orange-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs mono w-10 text-right ${isCritical ? 'text-red-400' : isLow ? 'text-orange-400' : 'text-slate-400'}`}>
        {qty} / {reorder}
      </span>
    </div>
  )
}

function StockoutBadge({ days }) {
  if (days === null || days === undefined) return <span className="text-slate-500 text-xs">—</span>
  const cls = days <= 7 ? 'text-red-400 bg-red-500/10 border border-red-500/20' :
    days <= 14 ? 'text-orange-400 bg-orange-500/10 border border-orange-500/20' :
    days <= 30 ? 'text-yellow-400 bg-yellow-500/10 border border-yellow-500/20' :
    'text-slate-400'
  return (
    <span className={`px-2 py-0.5 rounded text-xs mono ${cls}`}>
      {days}d
    </span>
  )
}

export default function CriticalParts() {
  const [parts, setParts] = useState([])
  const [forecast, setForecast] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([partsAPI.getCriticalWatchlist(), partsAPI.getStockoutForecast()])
      .then(([partsRes, forecastRes]) => {
        setParts(partsRes.data)
        setForecast(forecastRes.data)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const criticalCount = parts.filter(p => p.risk_score >= 80).length
  const belowReorder = parts.filter(p => p.inventory && p.inventory.quantity_on_hand <= p.inventory.reorder_point).length
  const delayedPos = parts.filter(p => p.active_po?.status === 'DELAYED').length

  const chartData = parts.slice(0, 10).map(p => ({
    name: p.part_number.split('-').slice(-1)[0],
    fullName: p.part_number,
    stock: p.inventory?.quantity_on_hand ?? 0,
    reorder: p.inventory?.reorder_point ?? 0,
    risk: p.risk_score,
  }))

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading parts data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Critical Parts Watchlist</h1>
        <p className="text-slate-400 text-sm mt-1">High-risk parts requiring immediate attention</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard icon={AlertTriangle} value={criticalCount} label="Critical Risk Parts (Score ≥ 80)" color="red" critical={criticalCount > 0} />
        <StatCard icon={Package} value={belowReorder} label="Parts Below Reorder Point" color="orange" />
        <StatCard icon={Clock} value={delayedPos} label="Delayed Purchase Orders" color="yellow" />
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl">
        <div className="p-5 border-b border-gray-800 flex items-center justify-between">
          <h2 className="font-semibold text-slate-100">Parts Watchlist</h2>
          <span className="text-xs text-slate-500">{parts.length} parts flagged</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-5 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Part #</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Category</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Platform</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Stock / ROP</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Supplier</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Risk</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Stockout</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">PO</th>
              </tr>
            </thead>
            <tbody>
              {parts.map(p => (
                <tr
                  key={p.id}
                  className={`border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors ${
                    p.risk_score >= 80 ? 'border-l-2 border-l-red-500' : p.risk_score >= 60 ? 'border-l-2 border-l-orange-500' : ''
                  }`}
                >
                  <td className="px-5 py-3 mono text-sky-400 font-medium text-xs">{p.part_number}</td>
                  <td className="px-4 py-3 text-slate-300 max-w-xs">
                    <div className="truncate">{p.name}</div>
                    {p.is_single_source && (
                      <span className="text-xs text-red-400 mono">SINGLE SOURCE</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-slate-400 bg-gray-800 px-2 py-0.5 rounded">{p.category}</span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400 max-w-24 truncate">{p.platform_compatibility}</td>
                  <td className="px-4 py-3 w-36">
                    <StockBar qty={p.inventory?.quantity_on_hand ?? 0} reorder={p.inventory?.reorder_point ?? 0} />
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400 max-w-32 truncate">{p.supplier_name}</td>
                  <td className="px-4 py-3"><RiskBadge score={p.risk_score} /></td>
                  <td className="px-4 py-3"><StockoutBadge days={p.stockout_days} /></td>
                  <td className="px-4 py-3">
                    {p.active_po ? (
                      <span className={`text-xs mono px-1.5 py-0.5 rounded ${
                        p.active_po.status === 'DELAYED'
                          ? 'bg-red-500/15 text-red-400 border border-red-500/30'
                          : 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                      }`}>
                        {p.active_po.status === 'DELAYED' ? `DEL+${p.active_po.delay_days}d` : p.active_po.status}
                      </span>
                    ) : <span className="text-slate-600 text-xs">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="font-semibold text-slate-100 mb-4">Stock Levels vs Reorder Points — Top 10 Risky Parts</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '8px', color: '#e2e8f0' }}
              formatter={(value, name) => [value, name === 'stock' ? 'On Hand' : 'Reorder Point']}
            />
            <Legend formatter={v => v === 'stock' ? 'On Hand' : 'Reorder Point'} wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
            <Bar dataKey="stock" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            <Bar dataKey="reorder" fill="#f97316" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
