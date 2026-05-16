import { AlertTriangle, X } from 'lucide-react'
import { useState } from 'react'

export function AlertBanner({ alerts = [] }) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed || alerts.length === 0) return null

  const criticalCount = alerts.filter(a => a.priority === 'CRITICAL').length
  const highCount = alerts.filter(a => a.priority === 'HIGH').length

  return (
    <div className="bg-red-950/60 border border-red-500/40 rounded-xl p-4 flex items-start gap-3 critical-glow">
      <AlertTriangle size={20} className="text-red-400 shrink-0 mt-0.5" />
      <div className="flex-1">
        <div className="font-semibold text-red-300">
          ACTIVE ALERTS: {criticalCount} CRITICAL, {highCount} HIGH PRIORITY
        </div>
        <div className="text-sm text-red-400/80 mt-1 space-y-1">
          {alerts.slice(0, 2).map(a => (
            <div key={a.id} className="flex items-start gap-1">
              <span className="text-red-500/60">•</span>
              <span>{a.title}</span>
            </div>
          ))}
          {alerts.length > 2 && (
            <div className="text-red-400/60">+{alerts.length - 2} more alerts</div>
          )}
        </div>
      </div>
      <button onClick={() => setDismissed(true)} className="text-red-400/60 hover:text-red-400 transition-colors">
        <X size={16} />
      </button>
    </div>
  )
}
