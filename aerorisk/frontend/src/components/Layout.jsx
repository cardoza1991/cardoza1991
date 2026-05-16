import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  Plane, Package, Users, TrendingUp, AlertTriangle,
  FileText, Activity, Shield, Zap, ChevronRight, RefreshCw
} from 'lucide-react'
import { agentAPI } from '../api/client'

const navItems = [
  { path: '/', label: 'Fleet Readiness', icon: Plane },
  { path: '/parts', label: 'Critical Parts', icon: Package },
  { path: '/suppliers', label: 'Supplier Risk', icon: Users },
  { path: '/maintenance', label: 'Predictive Maintenance', icon: TrendingUp },
  { path: '/recommendations', label: 'AI Recommendations', icon: AlertTriangle },
  { path: '/executive', label: 'Executive Summary', icon: FileText },
]

export function Layout({ children }) {
  const [currentTime, setCurrentTime] = useState(new Date())
  const [running, setRunning] = useState(false)
  const [cycleMsg, setCycleMsg] = useState(null)

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const handleRunCycle = async () => {
    setRunning(true)
    try {
      const { data } = await agentAPI.runCycle()
      setCycleMsg(`Agent cycle complete — ${data.open_recommendations} open recommendations`)
      setTimeout(() => setCycleMsg(null), 4000)
    } catch {
      setCycleMsg('Agent cycle failed')
      setTimeout(() => setCycleMsg(null), 3000)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden bg-aero-dark">
      {/* Sidebar */}
      <aside className="w-64 shrink-0 bg-gray-950 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="p-5 border-b border-gray-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-sky-500/10 border border-sky-500/30 rounded-lg">
              <Shield size={20} className="text-sky-400" />
            </div>
            <div>
              <div className="font-bold text-slate-100 text-sm leading-tight">AeroRisk AI</div>
              <div className="text-xs text-slate-500 leading-tight">Supply Chain Intel</div>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
            <span className="text-xs text-emerald-400 font-medium">SYSTEM LIVE</span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  isActive
                    ? 'bg-sky-500/15 text-sky-400 border border-sky-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-gray-800/60'
                }`
              }
            >
              <Icon size={16} />
              <span className="flex-1">{label}</span>
              <ChevronRight size={12} className="opacity-40" />
            </NavLink>
          ))}
        </nav>

        {/* System info */}
        <div className="p-4 border-t border-gray-800">
          <div className="text-xs text-slate-500 space-y-1">
            <div className="flex justify-between">
              <span>Version</span>
              <span className="text-slate-400 mono">v1.0.0</span>
            </div>
            <div className="flex justify-between">
              <span>AI Engine</span>
              <span className="text-sky-400 mono">ACTIVE</span>
            </div>
            <div className="flex justify-between">
              <span>Cycle</span>
              <span className="text-slate-400 mono">60s</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 bg-gray-950/80 border-b border-gray-800 flex items-center px-6 gap-4 shrink-0 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-sky-400" />
            <span className="font-semibold text-slate-100">AeroRisk AI</span>
            <span className="text-slate-600">—</span>
            <span className="text-slate-400 text-sm">Aerospace Supply Chain Risk Intelligence</span>
          </div>

          <div className="flex-1" />

          {cycleMsg && (
            <div className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg">
              {cycleMsg}
            </div>
          )}

          <div className="text-xs mono text-slate-400 bg-gray-800 px-3 py-1.5 rounded-lg">
            {currentTime.toISOString().slice(0, 19).replace('T', ' ')} UTC
          </div>

          <button
            onClick={handleRunCycle}
            disabled={running}
            className="flex items-center gap-2 px-4 py-1.5 bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 text-sky-400 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
          >
            {running ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              <Zap size={14} />
            )}
            Run Agent Cycle
          </button>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
