import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { TrendingUp, AlertTriangle, CheckCircle, Clock, Wrench } from 'lucide-react'
import { fleetAPI } from '../api/client'

function EventCard({ event, tailNumber, platform }) {
  const isUrgent = !event.part_available && event.requires_part
  const statusColors = {
    SCHEDULED: 'text-sky-400 bg-sky-500/10 border border-sky-500/20',
    IN_PROGRESS: 'text-yellow-400 bg-yellow-500/10 border border-yellow-500/20',
    COMPLETED: 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20',
    DEFERRED: 'text-slate-400 bg-slate-500/10 border border-slate-500/20',
  }
  const typeColors = {
    UNSCHEDULED: 'text-red-400',
    REPAIR: 'text-orange-400',
    INSPECTION: 'text-sky-400',
    SCHEDULED: 'text-emerald-400',
  }

  return (
    <div className={`rounded-lg border p-4 ${isUrgent ? 'border-red-500/40 bg-red-950/20 critical-glow' : 'border-gray-800 bg-gray-900'}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-semibold ${typeColors[event.event_type] || 'text-slate-400'}`}>
              {event.event_type}
            </span>
            <span className="text-slate-600">·</span>
            <span className="text-xs mono text-sky-400">{tailNumber}</span>
            <span className="text-xs text-slate-500">{platform}</span>
          </div>
          <div className="text-sm text-slate-300 mb-2 leading-relaxed">{event.description}</div>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <div className="flex items-center gap-1">
              <Clock size={11} />
              {event.scheduled_date ? new Date(event.scheduled_date).toLocaleDateString() : '—'}
            </div>
            <div className="flex items-center gap-1">
              <Wrench size={11} />
              {event.technician}
            </div>
          </div>
        </div>
        <div className="text-right shrink-0">
          <span className={`text-xs px-2 py-0.5 rounded mono ${statusColors[event.status] || 'text-slate-400'}`}>
            {event.status}
          </span>
          {event.requires_part && (
            <div className={`text-xs mt-1.5 flex items-center justify-end gap-1 ${event.part_available ? 'text-emerald-400' : 'text-red-400'}`}>
              {event.part_available ? <CheckCircle size={11} /> : <AlertTriangle size={11} />}
              {event.part_available ? 'Part OK' : 'NO PART'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function MaintenanceRisk() {
  const [aircraft, setAircraft] = useState([])
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fleetAPI.getAll()
      .then(res => {
        setAircraft(res.data)
        // Load detail for each aircraft to get maintenance events
        return Promise.all(
          res.data.map(ac =>
            fleetAPI.getDetail(ac.tail_number)
              .then(detail => detail.data.maintenance_events?.map(e => ({
                ...e,
                tail_number: ac.tail_number,
                platform: ac.platform,
              })) || [])
          )
        )
      })
      .then(allEvents => {
        const flat = allEvents.flat()
          .filter(e => e.status !== 'COMPLETED')
          .sort((a, b) => new Date(a.scheduled_date) - new Date(b.scheduled_date))
        setEvents(flat)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Build weekly maintenance chart
  const now = new Date()
  const weeklyData = Array.from({ length: 8 }, (_, i) => {
    const weekStart = new Date(now)
    weekStart.setDate(now.getDate() + i * 7)
    const weekEnd = new Date(weekStart)
    weekEnd.setDate(weekStart.getDate() + 7)
    const weekEvents = events.filter(e => {
      if (!e.scheduled_date) return false
      const d = new Date(e.scheduled_date)
      return d >= weekStart && d < weekEnd
    })
    return {
      week: `W${i + 1}`,
      label: weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      total: weekEvents.length,
      blocked: weekEvents.filter(e => !e.part_available && e.requires_part).length,
      ready: weekEvents.filter(e => !e.requires_part || e.part_available).length,
    }
  })

  const blockedCount = events.filter(e => !e.part_available && e.requires_part).length
  const urgentCount = events.filter(e => e.event_type === 'UNSCHEDULED' || e.status === 'IN_PROGRESS').length
  const scheduledCount = events.filter(e => e.status === 'SCHEDULED').length

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">Loading maintenance data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Predictive Maintenance Risk</h1>
        <p className="text-slate-400 text-sm mt-1">Upcoming maintenance events and parts availability forecast</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-3xl font-bold text-orange-400 mb-1">{blockedCount}</div>
          <div className="text-sm text-slate-400">Events Lacking Required Parts</div>
          {blockedCount > 0 && <div className="text-xs text-red-400 mt-1">Immediate action required</div>}
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-3xl font-bold text-yellow-400 mb-1">{urgentCount}</div>
          <div className="text-sm text-slate-400">Unscheduled / In-Progress Events</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="text-3xl font-bold text-sky-400 mb-1">{scheduledCount}</div>
          <div className="text-sm text-slate-400">Upcoming Scheduled Events</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Timeline events */}
        <div className="space-y-3">
          <h2 className="font-semibold text-slate-100">Upcoming Maintenance Events</h2>
          {events.length === 0 ? (
            <div className="text-slate-500 text-sm">No upcoming events</div>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
              {events.map(e => (
                <EventCard key={e.id} event={e} tailNumber={e.tail_number} platform={e.platform} />
              ))}
            </div>
          )}
        </div>

        {/* Weekly chart */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="font-semibold text-slate-100 mb-4">Maintenance Load — Next 8 Weeks</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={weeklyData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 10 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: '8px', color: '#e2e8f0' }}
                formatter={(val, name) => [val, name === 'ready' ? 'Ready' : 'Parts Blocked']}
              />
              <Bar dataKey="ready" stackId="a" fill="#0ea5e9" radius={[0, 0, 0, 0]} name="ready" />
              <Bar dataKey="blocked" stackId="a" fill="#ef4444" radius={[4, 4, 0, 0]} name="blocked" />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 text-xs text-slate-500">
            <div className="flex items-center gap-1"><div className="w-3 h-2 rounded-sm bg-sky-500" />Parts Ready</div>
            <div className="flex items-center gap-1"><div className="w-3 h-2 rounded-sm bg-red-500" />Parts Blocked</div>
          </div>
        </div>
      </div>
    </div>
  )
}
