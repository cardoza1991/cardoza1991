import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  Shield, DollarSign, Plane, Clock, ShieldCheck, AlertOctagon, Printer,
  Radio, Layers, Bot, Lock,
} from 'lucide-react'
import { scenariosAPI } from '../api/client'

const SEVERITY = {
  CRITICAL: { tag: 'bg-red-500/20 text-red-300 border-red-500/40', dot: 'bg-red-500' },
  HIGH:     { tag: 'bg-orange-500/20 text-orange-300 border-orange-500/40', dot: 'bg-orange-500' },
  MEDIUM:   { tag: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40', dot: 'bg-yellow-500' },
  LOW:      { tag: 'bg-sky-500/15 text-sky-300 border-sky-500/40', dot: 'bg-sky-500' },
}

function Tag({ severity, children }) {
  const cls = (SEVERITY[severity] || SEVERITY.LOW).tag
  return <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold tracking-wider ${cls}`}>{children || severity}</span>
}

function fmtUSD(n) {
  if (n == null) return '$0'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${Math.round(n)}`
}

function platformString(platforms) {
  if (!platforms) return '—'
  return Object.entries(platforms).sort((a,b)=>b[1]-a[1]).map(([p,c])=>`${c} ${p}`).join(', ') || '—'
}

export default function SharedScenario() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    scenariosAPI.getByShareToken(token)
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.status === 404 ? 'not_found' : 'error'))
  }, [token])

  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
        <div className="text-center max-w-md">
          <Lock size={32} className="text-slate-500 mx-auto mb-3" />
          <h1 className="text-xl text-slate-100 font-semibold mb-1">Scenario not found</h1>
          <p className="text-sm text-slate-500">This share link is invalid or has been revoked.</p>
        </div>
      </div>
    )
  }
  if (!data) {
    return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-slate-400">Loading…</div>
  }

  const snap = data.snapshot || {}
  const sev = data.severity || 'LOW'
  const triggered = data.trigger === 'AUTO_INTEL'

  return (
    <div className="min-h-screen bg-gray-950 text-slate-200 print:bg-white print:text-black">
      {/* Header bar (hidden in print) */}
      <header className="border-b border-gray-800 bg-gray-950 print:hidden">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center gap-3">
          <div className="p-1.5 bg-sky-500/10 border border-sky-500/30 rounded">
            <Shield size={16} className="text-sky-400" />
          </div>
          <div>
            <div className="font-bold text-sm text-slate-100">AeroRisk AI</div>
            <div className="text-[10px] text-slate-500 -mt-0.5">Autonomous Supply Chain Intelligence</div>
          </div>
          <div className="flex-1" />
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-slate-300 rounded border border-gray-700"
          >
            <Printer size={12} />
            Print / Save as PDF
          </button>
          <Link to="/" className="text-xs text-sky-400 hover:text-sky-300">Open full dashboard →</Link>
        </div>
      </header>

      {/* Cover */}
      <article className="max-w-5xl mx-auto px-6 py-10 print:py-4 space-y-6 print:space-y-3">
        <div className="space-y-2 print:space-y-1">
          <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-slate-500 print:text-gray-600">
            <span>Operational Impact Brief</span>
            <span>·</span>
            <span>{data.horizon_days}-day horizon</span>
            <span>·</span>
            <span>Generated {new Date(data.created_at + 'Z').toLocaleString()}</span>
          </div>
          <h1 className="text-3xl font-bold text-slate-100 print:text-black flex items-center gap-3 flex-wrap">
            {data.supplier_name}
            <Tag severity={sev} />
            {triggered && (
              <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-red-500/15 text-red-300 border border-red-500/40 rounded font-semibold tracking-wider print:hidden">
                <Bot size={10} />
                AUTO-TRIGGERED
              </span>
            )}
          </h1>
          {data.trigger_signal_title && (
            <div className="text-xs text-slate-400 print:text-gray-700">
              Triggered by <span className="mono text-slate-300">{data.trigger_signal_source}</span> — {data.trigger_signal_title}
            </div>
          )}
        </div>

        {/* The Line */}
        <blockquote className="text-lg leading-relaxed text-slate-100 print:text-black border-l-2 border-sky-500/60 pl-4 italic">
          {data.one_liner}
        </blockquote>

        {/* Headline numbers */}
        <div className="grid grid-cols-4 gap-3 print:gap-2">
          <Cell icon={DollarSign} label="Dollar exposure" value={fmtUSD(data.dollar_exposure_usd)} sub={`${data.horizon_days}-day horizon`} color="red" />
          <Cell icon={Plane} label="Aircraft affected" value={data.aircraft_affected} sub={platformString(snap.platforms)} color="orange" />
          <Cell icon={Clock} label="Production delay" value={`${data.production_delay_days}d`} sub={`Qual ${snap.qualification_days ?? 120}d`} color="yellow" />
          <Cell icon={ShieldCheck} label="Confidence" value={`${Math.round((data.confidence || 0) * 100)}%`} sub="Reconstructible" color="emerald" />
        </div>

        {/* Drilldowns */}
        <div className="grid grid-cols-2 gap-4 print:gap-3 print:grid-cols-1">
          <Section title="Affected aircraft" icon={Plane} accent="orange">
            {(snap.affected_aircraft || []).slice(0, 8).map(a => (
              <div key={a.tail_number} className="flex items-center gap-2 text-xs py-1.5 border-b border-gray-800/40 last:border-0 print:border-gray-300">
                <span className="mono text-slate-100 print:text-black w-20">{a.tail_number}</span>
                <span className="text-slate-400 print:text-gray-700">{a.platform}</span>
                <span className="text-slate-600">·</span>
                <span className="text-slate-500 print:text-gray-600">{a.squadron}</span>
                <div className="flex-1" />
                <span className="text-slate-400 print:text-gray-700">{a.days_to_impact}d</span>
                <span className="text-red-300 mono">{fmtUSD(a.sortie_value_at_risk)}</span>
              </div>
            ))}
            {(!snap.affected_aircraft || snap.affected_aircraft.length === 0) && (
              <div className="text-xs text-slate-500 italic">None in horizon.</div>
            )}
          </Section>

          <Section title="Ranked alternates" icon={ShieldCheck} accent="emerald">
            {(snap.alternates || []).map((a, i) => (
              <div key={a.supplier_id} className="text-xs py-1.5 border-b border-gray-800/40 last:border-0 print:border-gray-300">
                <div className="flex items-center gap-2">
                  <span className="mono text-slate-500">#{i+1}</span>
                  <span className="font-medium text-slate-100 print:text-black flex-1 truncate">{a.name}</span>
                  {a.has_active_intel && <Tag severity="HIGH">INTEL</Tag>}
                  <span className="mono text-emerald-300 print:text-emerald-700">{a.rank_score.toFixed(2)}</span>
                </div>
                <div className="text-[11px] text-slate-500 print:text-gray-600">
                  {a.country} · {a.overlap_part_count} overlapping parts · OTD {Math.round(a.on_time_delivery_rate*100)}%
                </div>
              </div>
            ))}
            {(!snap.alternates || snap.alternates.length === 0) && (
              <div className="text-xs text-red-400 italic">No approved alternates — engineering review required.</div>
            )}
          </Section>

          <Section title="Top affected parts" icon={Layers} accent="yellow">
            {(snap.affected_parts || []).slice(0, 6).map(p => (
              <div key={p.part_number} className="text-xs py-1.5 border-b border-gray-800/40 last:border-0 print:border-gray-300">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="mono text-sky-300 print:text-sky-700">{p.part_number}</span>
                  {p.is_mission_critical && <Tag severity="CRITICAL">MC</Tag>}
                  {p.is_single_source && <Tag severity="HIGH">SS</Tag>}
                  <span className="text-slate-400 print:text-gray-700 truncate">{p.name}</span>
                </div>
                <div className="text-[11px] text-slate-500 print:text-gray-600">
                  {p.quantity_on_hand} on hand · {p.days_of_stock < 0 ? 'no consumption data' : `${p.days_of_stock}d of stock`}
                  {p.gap_days > 0 && <span className="text-orange-400 print:text-orange-700"> · {p.gap_days}d gap</span>}
                </div>
              </div>
            ))}
          </Section>

          <Section title="Cascading intel & playbook" icon={Radio} accent="sky">
            {(snap.cascading_signals || []).slice(0, 4).length > 0 && (
              <div className="mb-2">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 print:text-gray-600 mb-1">Active signals</div>
                {(snap.cascading_signals || []).slice(0, 4).map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs py-0.5">
                    <Tag severity={s.severity} />
                    <span className="mono text-[10px] text-slate-500">{s.source}</span>
                    <span className="text-slate-300 print:text-gray-800 truncate">{s.title}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="text-[10px] uppercase tracking-wider text-slate-500 print:text-gray-600 mb-1">Recommended actions</div>
            <ol className="text-xs text-slate-300 print:text-gray-800 space-y-1 list-decimal list-inside">
              {(snap.mitigation_actions || []).map((a, i) => <li key={i}>{a}</li>)}
            </ol>
          </Section>
        </div>

        <footer className="pt-6 border-t border-gray-800 print:border-gray-300 text-[10px] text-slate-500 print:text-gray-600 leading-relaxed">
          <div>
            AeroRisk AI · Autonomous Aerospace Supply Chain Intelligence ·
            {' '}Every number on this page is reconstructible from the underlying data model.
            No LLM hallucination, no synthetic embeddings — pure derived data.
          </div>
          <div className="mt-1 mono">Scenario {data.id} · Token {token.slice(0, 12)}…</div>
        </footer>
      </article>
    </div>
  )
}

function Cell({ icon: Icon, label, value, sub, color }) {
  const colors = {
    red: 'text-red-300 print:text-red-700',
    orange: 'text-orange-300 print:text-orange-700',
    yellow: 'text-yellow-300 print:text-yellow-700',
    emerald: 'text-emerald-300 print:text-emerald-700',
  }
  return (
    <div className="bg-gray-900/80 print:bg-white border border-gray-800 print:border-gray-300 rounded-lg p-4 print:p-2">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-400 print:text-gray-600 mb-1">
        <Icon size={11} className={colors[color]} />
        {label}
      </div>
      <div className={`text-2xl font-bold ${colors[color]} print:text-black`}>{value}</div>
      {sub && <div className="text-[11px] text-slate-500 print:text-gray-600 mt-0.5">{sub}</div>}
    </div>
  )
}

function Section({ title, icon: Icon, accent, children }) {
  const colors = {
    orange: 'text-orange-400', emerald: 'text-emerald-400',
    yellow: 'text-yellow-400', sky: 'text-sky-400',
  }
  return (
    <div className="bg-gray-900/50 print:bg-white border border-gray-800 print:border-gray-300 rounded-lg overflow-hidden">
      <div className="px-3 py-2 border-b border-gray-800 print:border-gray-300 flex items-center gap-2">
        <Icon size={12} className={colors[accent]} />
        <h3 className="text-xs font-semibold text-slate-200 print:text-black">{title}</h3>
      </div>
      <div className="p-3">{children}</div>
    </div>
  )
}
