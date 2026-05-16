import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'

export function StatCard({ icon: Icon, value, label, trend, trendLabel, color = 'blue', critical = false }) {
  const colorMap = {
    blue: 'text-sky-400',
    green: 'text-emerald-400',
    red: 'text-red-400',
    orange: 'text-orange-400',
    yellow: 'text-yellow-400',
    slate: 'text-slate-400',
  }

  const iconBgMap = {
    blue: 'bg-sky-500/10 border border-sky-500/20',
    green: 'bg-emerald-500/10 border border-emerald-500/20',
    red: 'bg-red-500/10 border border-red-500/20',
    orange: 'bg-orange-500/10 border border-orange-500/20',
    yellow: 'bg-yellow-500/10 border border-yellow-500/20',
    slate: 'bg-slate-500/10 border border-slate-500/20',
  }

  return (
    <div className={clsx(
      'bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-start gap-4',
      critical && 'critical-glow border-red-500/50'
    )}>
      {Icon && (
        <div className={clsx('p-2.5 rounded-lg', iconBgMap[color])}>
          <Icon size={20} className={colorMap[color]} />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className={clsx('text-2xl font-bold', colorMap[color])}>{value}</div>
        <div className="text-sm text-slate-400 mt-0.5">{label}</div>
        {trendLabel && (
          <div className={clsx(
            'text-xs mt-1 flex items-center gap-1',
            trend === 'up' ? 'text-red-400' : trend === 'down' ? 'text-emerald-400' : 'text-slate-500'
          )}>
            {trend === 'up' ? <TrendingUp size={12} /> : trend === 'down' ? <TrendingDown size={12} /> : <Minus size={12} />}
            {trendLabel}
          </div>
        )}
      </div>
    </div>
  )
}
