export function RiskBadge({ score, level }) {
  const derived = level || (score >= 80 ? 'CRITICAL' : score >= 60 ? 'HIGH' : score >= 40 ? 'MEDIUM' : 'LOW')
  const classes = {
    CRITICAL: 'bg-red-500/20 text-red-400 border border-red-500/40',
    HIGH: 'bg-orange-500/20 text-orange-400 border border-orange-500/40',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40',
    LOW: 'bg-green-500/20 text-green-400 border border-green-500/40',
  }
  return (
    <span className={`px-2 py-1 rounded text-xs font-semibold mono ${classes[derived]}`}>
      {derived}{score !== undefined ? ` ${Math.round(score)}` : ''}
    </span>
  )
}
