import { useEffect, useMemo, useState } from 'react'
import {
  Zap, Target, Plane, DollarSign, Clock, ShieldCheck, AlertOctagon, Radio,
  Copy, Check, FileText, ChevronRight, Layers, Activity, Bot, Link2, Bell,
} from 'lucide-react'
import { impactAPI, suppliersAPI, scenariosAPI } from '../api/client'

const SEVERITY = {
  CRITICAL: { ring: 'ring-red-500/60', tag: 'bg-red-500/20 text-red-300 border-red-500/40' },
  HIGH:     { ring: 'ring-orange-500/60', tag: 'bg-orange-500/20 text-orange-300 border-orange-500/40' },
  MEDIUM:   { ring: 'ring-yellow-500/50', tag: 'bg-yellow-500/15 text-yellow-300 border-yellow-500/40' },
  LOW:      { ring: 'ring-sky-500/40', tag: 'bg-sky-500/15 text-sky-300 border-sky-500/40' },
}

function Tag({ severity, children }) {
  const cls = (SEVERITY[severity] || SEVERITY.LOW).tag
  return <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold tracking-wider ${cls}`}>{children || severity}</span>
}

function HeadlineCard({ icon: Icon, label, value, sub, accent = 'sky', big }) {
  const accents = {
    sky: 'text-sky-300',
    red: 'text-red-300',
    orange: 'text-orange-300',
    yellow: 'text-yellow-300',
    emerald: 'text-emerald-300',
  }
  return (
    <div className="bg-gray-900/70 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center gap-2 text-xs text-slate-400 mb-2 uppercase tracking-wider">
        <Icon size={14} className={accents[accent]} />
        {label}
      </div>
      <div className={`font-bold ${accents[accent]} ${big ? 'text-3xl' : 'text-2xl'}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  )
}

// Minimal markdown → HTML for the executive brief. Handles only what the
// brief actually emits: ATX headings, bullet lists, ordered lists, **bold**,
// `code`, em-rules, paragraphs. Inline HTML is escaped first so brief content
// can't break out of the layout.
function renderBriefHtml(md) {
  const escape = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const lines = md.split('\n')
  let body = ''
  let list = null   // 'ul' | 'ol' | null
  const closeList = () => { if (list) { body += `</${list}>`; list = null } }
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '')
    if (!line) { closeList(); continue }
    let m
    if ((m = line.match(/^#\s+(.*)/))) { closeList(); body += `<h1>${inline(m[1])}</h1>`; continue }
    if ((m = line.match(/^##\s+(.*)/))) { closeList(); body += `<h2>${inline(m[1])}</h2>`; continue }
    if ((m = line.match(/^###\s+(.*)/))) { closeList(); body += `<h3>${inline(m[1])}</h3>`; continue }
    if (line === '---') { closeList(); body += '<hr/>'; continue }
    if ((m = line.match(/^\s*-\s+(.*)/))) {
      if (list !== 'ul') { closeList(); body += '<ul>'; list = 'ul' }
      body += `<li>${inline(m[1])}</li>`; continue
    }
    if ((m = line.match(/^\s*\d+\.\s+(.*)/))) {
      if (list !== 'ol') { closeList(); body += '<ol>'; list = 'ol' }
      body += `<li>${inline(m[1])}</li>`; continue
    }
    closeList()
    body += `<p>${inline(line)}</p>`
  }
  closeList()
  function inline(s) {
    return escape(s)
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
  }
  return `<!doctype html><html><head><meta charset="utf-8"><title>AeroRisk Executive Brief</title>
<style>
  @page { size: letter; margin: 0.6in; }
  body { font-family: 'Inter', system-ui, -apple-system, sans-serif; color: #111; max-width: 7.2in; margin: 0 auto; padding: 24px; line-height: 1.5; }
  h1 { font-size: 22px; border-bottom: 2px solid #0ea5e9; padding-bottom: 6px; margin: 0 0 8px; }
  h2 { font-size: 16px; margin-top: 20px; margin-bottom: 6px; color: #0c4a6e; }
  h3 { font-size: 14px; margin-top: 14px; margin-bottom: 4px; }
  p { margin: 6px 0; }
  ul, ol { margin: 6px 0 6px 24px; }
  li { margin: 2px 0; }
  hr { border: none; border-top: 1px solid #d1d5db; margin: 18px 0; }
  strong { color: #0c4a6e; }
  code { font-family: 'JetBrains Mono', monospace; font-size: 90%; background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }
</style></head><body>${body}</body></html>`
}

function formatUSD(n) {
  if (n == null) return '$0'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`
  return `$${Math.round(n)}`
}

function platformString(platforms) {
  if (!platforms) return '—'
  return Object.entries(platforms)
    .sort((a, b) => b[1] - a[1])
    .map(([p, c]) => `${c} ${p}`)
    .join(', ') || '—'
}

export default function OperationalImpact() {
  const [suppliers, setSuppliers] = useState([])
  const [supplierId, setSupplierId] = useState(null)
  const [horizon, setHorizon] = useState(90)
  const [impact, setImpact] = useState(null)
  const [topRisks, setTopRisks] = useState([])
  const [running, setRunning] = useState(false)
  const [brief, setBrief] = useState('')
  const [briefOpen, setBriefOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [autoScenarios, setAutoScenarios] = useState([])
  const [shareCopied, setShareCopied] = useState(false)

  const loadAutoFeed = () => {
    scenariosAPI.list({ trigger: 'AUTO_INTEL', limit: 10 })
      .then(r => setAutoScenarios(r.data))
      .catch(console.error)
  }

  // Boot: load suppliers + top risks + autonomous feed
  useEffect(() => {
    Promise.all([
      suppliersAPI.getRiskMap().then(r => setSuppliers(r.data)),
      impactAPI.topRisks({ horizon_days: 90, top_n: 5 }).then(r => setTopRisks(r.data)),
    ]).catch(console.error)
    loadAutoFeed()
    // Poll the autonomous feed every 20s so new scenarios appear during a demo.
    const t = setInterval(loadAutoFeed, 20_000)
    return () => clearInterval(t)
  }, [])

  // Default-select the top supplier
  useEffect(() => {
    if (supplierId == null && topRisks.length > 0) {
      setSupplierId(topRisks[0].supplier_id)
    }
  }, [topRisks, supplierId])

  // When supplier or horizon changes, fetch impact
  useEffect(() => {
    if (supplierId == null) return
    impactAPI.forSupplier(supplierId, { horizon_days: horizon })
      .then(r => setImpact(r.data))
      .catch(console.error)
  }, [supplierId, horizon])

  const runSimulation = async () => {
    if (supplierId == null) return
    setRunning(true)
    try {
      const { data } = await impactAPI.simulate({ supplier_id: supplierId, horizon_days: horizon })
      setImpact(data)
      const refreshed = await impactAPI.topRisks({ horizon_days: horizon, top_n: 5 })
      setTopRisks(refreshed.data)
    } catch (e) { console.error(e) } finally {
      // brief delay so the animation is visible
      setTimeout(() => setRunning(false), 400)
    }
  }

  const copyShareLink = async () => {
    if (!impact?.share_token) return
    const url = `${window.location.origin}/share/${impact.share_token}`
    try {
      await navigator.clipboard.writeText(url)
      setShareCopied(true)
      setTimeout(() => setShareCopied(false), 1800)
    } catch {}
  }

  const openBrief = async () => {
    try {
      const { data } = await impactAPI.brief({ horizon_days: horizon })
      setBrief(data.markdown)
      setBriefOpen(true)
    } catch (e) { console.error(e) }
  }

  const copyBrief = async () => {
    try {
      await navigator.clipboard.writeText(brief)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {}
  }

  // Render the markdown brief into a clean printable HTML document in a new
  // window, then trigger the browser's print/Save-as-PDF dialog. This avoids
  // a server-side PDF dependency (WeasyPrint/cairo/etc).
  const printBrief = () => {
    if (!brief) return
    const html = renderBriefHtml(brief)
    const w = window.open('', '_blank', 'noopener,noreferrer,width=900,height=1100')
    if (!w) return
    w.document.open()
    w.document.write(html)
    w.document.close()
    // Allow the document to layout before printing.
    w.onload = () => { try { w.focus(); w.print() } catch {} }
  }

  const supplierOptions = useMemo(
    () => [...suppliers].sort((a, b) => b.risk_score - a.risk_score),
    [suppliers],
  )

  const sev = impact?.severity || 'LOW'
  const ring = (SEVERITY[sev] || SEVERITY.LOW).ring

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Target size={22} className="text-sky-400" />
            Operational Impact Engine
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            If a supplier fails today, this is what breaks. Every number is reconstructible from the data model.
          </p>
        </div>
        <button
          onClick={openBrief}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 rounded-lg text-sm font-medium transition"
        >
          <FileText size={14} />
          Generate Executive Brief
        </button>
      </div>

      {/* Autonomous trigger feed */}
      <div className="bg-gradient-to-br from-red-950/30 to-gray-900 border border-red-500/20 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-red-500/20 flex items-center gap-2">
          <Bot size={14} className="text-red-400" />
          <h2 className="font-semibold text-slate-100">Autonomous trigger feed</h2>
          <span className="text-[10px] px-1.5 py-0.5 bg-red-500/20 text-red-300 border border-red-500/40 rounded font-semibold tracking-wider">LIVE</span>
          <span className="text-xs text-slate-500 ml-2">
            New CRITICAL intel → auto-impact → operator pinged. {autoScenarios.length} recent.
          </span>
        </div>
        <div className="divide-y divide-gray-800/60 max-h-[200px] overflow-y-auto">
          {autoScenarios.length === 0 && (
            <div className="p-4 text-center text-xs text-slate-500 italic">
              No autonomous scenarios yet. Click <span className="text-sky-400">Refresh intel feeds</span> on Supplier Risk to inject CRITICAL signals.
            </div>
          )}
          {autoScenarios.map(sc => (
            <button
              key={sc.id}
              onClick={() => setSupplierId(sc.supplier_id)}
              className="w-full text-left p-3 hover:bg-gray-800/40 transition flex items-center gap-3"
            >
              <Tag severity={sc.severity} />
              <Bell size={11} className={sc.notified ? 'text-emerald-400' : 'text-slate-500'} />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-slate-200 truncate">
                  <span className="font-semibold">{sc.supplier_name}</span>
                  <span className="text-slate-500"> · triggered by </span>
                  <span className="mono text-slate-400">{sc.trigger_signal_source}</span>
                  <span className="text-slate-500"> · {sc.trigger_signal_title}</span>
                </div>
                <div className="text-[11px] text-slate-500 truncate">{sc.one_liner}</div>
              </div>
              <div className="text-right text-xs shrink-0">
                <div className="text-red-300 font-semibold">{formatUSD(sc.dollar_exposure_usd)}</div>
                <div className="text-slate-500">{new Date(sc.created_at + 'Z').toLocaleTimeString()}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Top risks leaderboard */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-800 flex items-center gap-2">
          <Layers size={14} className="text-orange-400" />
          <h2 className="font-semibold text-slate-100">Top operational risks across the catalog</h2>
          <span className="text-xs text-slate-500 ml-auto">{horizon}-day horizon</span>
        </div>
        <div className="divide-y divide-gray-800">
          {topRisks.length === 0 && (
            <div className="p-6 text-center text-sm text-slate-500">Computing risk portfolio…</div>
          )}
          {topRisks.map((r, i) => {
            const isSelected = supplierId === r.supplier_id
            return (
              <button
                key={r.supplier_id}
                onClick={() => setSupplierId(r.supplier_id)}
                className={`w-full text-left p-4 hover:bg-gray-800/40 transition ${isSelected ? 'bg-gray-800/30' : ''}`}
              >
                <div className="flex items-center gap-3">
                  <div className={`text-2xl font-black mono ${
                    i === 0 ? 'text-red-400' : i === 1 ? 'text-orange-400' : 'text-slate-500'
                  } w-8`}>{i + 1}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-semibold text-slate-100">{r.supplier_name}</span>
                      <Tag severity={r.severity} />
                      <span className="text-xs text-slate-500">conf {Math.round(r.confidence * 100)}%</span>
                    </div>
                    <div className="text-xs text-slate-400 line-clamp-2">{r.one_liner}</div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xl font-bold text-red-300">{formatUSD(r.dollar_exposure_usd)}</div>
                    <div className="text-xs text-slate-500">{r.aircraft_affected} aircraft · {r.production_delay_days}d delay</div>
                  </div>
                  <ChevronRight size={14} className="text-slate-600 shrink-0" />
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Simulator controls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-end gap-3 flex-wrap">
          <div className="flex-1 min-w-[240px]">
            <label className="text-xs text-slate-400 uppercase tracking-wider mb-1 block">Simulate failure of</label>
            <select
              value={supplierId ?? ''}
              onChange={e => setSupplierId(Number(e.target.value))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
            >
              <option value="" disabled>Select a supplier…</option>
              {supplierOptions.map(s => (
                <option key={s.id} value={s.id}>
                  {s.name} {s.intel_signal_count > 0 ? `· ${s.intel_signal_count} intel signal(s)` : ''}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 uppercase tracking-wider mb-1 block">Horizon</label>
            <select
              value={horizon}
              onChange={e => setHorizon(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-slate-100"
            >
              <option value={30}>30 days</option>
              <option value={60}>60 days</option>
              <option value={90}>90 days</option>
              <option value={180}>180 days</option>
              <option value={365}>1 year</option>
            </select>
          </div>
          <button
            onClick={runSimulation}
            disabled={running || supplierId == null}
            className="flex items-center gap-2 px-5 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-200 rounded-lg text-sm font-semibold transition disabled:opacity-50"
          >
            <Zap size={14} className={running ? 'animate-pulse' : ''} />
            {running ? 'Simulating…' : 'Simulate failure'}
          </button>
        </div>
      </div>

      {/* Impact result */}
      {impact && (
        <div className={`bg-gray-900 border border-gray-800 rounded-xl p-6 ring-2 ${ring} transition-all`}>
          <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <AlertOctagon size={16} className="text-red-400" />
                <h2 className="text-lg font-bold text-slate-100">{impact.supplier_name}</h2>
                <Tag severity={impact.severity} />
                <span className="text-xs text-slate-500">confidence {Math.round(impact.confidence * 100)}%</span>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                {impact.executive_one_liner}
              </p>
            </div>
            {impact.share_token && (
              <button
                onClick={copyShareLink}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-slate-300 rounded border border-gray-700 shrink-0"
                title="Copy a public read-only link to this scenario"
              >
                {shareCopied ? <Check size={12} className="text-emerald-400" /> : <Link2 size={12} />}
                {shareCopied ? 'Copied' : 'Copy share link'}
              </button>
            )}
          </div>

          {/* Headline numbers */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <HeadlineCard
              icon={DollarSign} label="Dollar exposure"
              value={formatUSD(impact.dollar_exposure_usd)}
              sub={`Over ${impact.horizon_days}-day horizon`}
              accent="red" big
            />
            <HeadlineCard
              icon={Plane} label="Aircraft affected"
              value={impact.aircraft_affected}
              sub={platformString(impact.platforms)}
              accent="orange" big
            />
            <HeadlineCard
              icon={Clock} label="Production delay"
              value={`${impact.production_delay_days}d`}
              sub={`Qualification: ${impact.qualification_days}d`}
              accent="yellow" big
            />
            <HeadlineCard
              icon={ShieldCheck} label="Alternates ranked"
              value={impact.alternates?.length || 0}
              sub={impact.alternates?.[0]?.name || 'None approved'}
              accent={impact.alternates?.length ? 'emerald' : 'red'}
              big
            />
          </div>

          {/* Drilldowns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Affected aircraft */}
            <div className="bg-gray-950/50 border border-gray-800 rounded-lg overflow-hidden">
              <div className="px-4 py-2.5 border-b border-gray-800 flex items-center gap-2">
                <Plane size={13} className="text-orange-400" />
                <h3 className="text-sm font-semibold text-slate-200">Affected aircraft</h3>
                <span className="text-xs text-slate-500 ml-auto">{impact.affected_aircraft.length}</span>
              </div>
              <div className="divide-y divide-gray-800/60 max-h-[260px] overflow-y-auto">
                {impact.affected_aircraft.length === 0 && (
                  <div className="p-4 text-xs text-slate-500 italic">No aircraft affected in this horizon.</div>
                )}
                {impact.affected_aircraft.map(a => (
                  <div key={a.tail_number} className="p-3 flex items-center gap-3">
                    <div>
                      <div className="font-mono text-sm text-slate-100">{a.tail_number}</div>
                      <div className="text-xs text-slate-500">{a.platform} · {a.squadron}</div>
                    </div>
                    <div className="flex-1" />
                    <div className="text-right text-xs">
                      <div className="text-slate-300">{a.days_to_impact}d to impact</div>
                      <div className="text-slate-500">{formatUSD(a.sortie_value_at_risk)} at risk</div>
                    </div>
                    <Tag severity={a.current_status === 'NMC' ? 'CRITICAL' : a.current_status === 'AT_RISK' ? 'HIGH' : a.current_status === 'PMC' ? 'MEDIUM' : 'LOW'}>
                      {a.current_status}
                    </Tag>
                  </div>
                ))}
              </div>
            </div>

            {/* Alternates */}
            <div className="bg-gray-950/50 border border-gray-800 rounded-lg overflow-hidden">
              <div className="px-4 py-2.5 border-b border-gray-800 flex items-center gap-2">
                <ShieldCheck size={13} className="text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-200">Ranked alternate suppliers</h3>
                <span className="text-xs text-slate-500 ml-auto">{impact.alternates.length}</span>
              </div>
              <div className="divide-y divide-gray-800/60 max-h-[260px] overflow-y-auto">
                {impact.alternates.length === 0 && (
                  <div className="p-4 text-xs text-red-400 italic">No approved alternates found — engineering review required.</div>
                )}
                {impact.alternates.map((a, i) => (
                  <div key={a.supplier_id} className="p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="mono text-xs text-slate-500">#{i + 1}</span>
                      <span className="text-sm font-medium text-slate-100 flex-1 truncate">{a.name}</span>
                      {a.has_active_intel && <Tag severity="HIGH">INTEL</Tag>}
                      <span className="text-xs mono text-emerald-300">{a.rank_score.toFixed(2)}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {a.country} · {a.overlap_part_count} overlapping parts · OTD {Math.round(a.on_time_delivery_rate * 100)}% · reliability {a.reliability_score.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Affected parts */}
            <div className="bg-gray-950/50 border border-gray-800 rounded-lg overflow-hidden">
              <div className="px-4 py-2.5 border-b border-gray-800 flex items-center gap-2">
                <Layers size={13} className="text-yellow-400" />
                <h3 className="text-sm font-semibold text-slate-200">Affected parts</h3>
                <span className="text-xs text-slate-500 ml-auto">{impact.affected_parts.length}</span>
              </div>
              <div className="divide-y divide-gray-800/60 max-h-[260px] overflow-y-auto">
                {impact.affected_parts.slice(0, 12).map(p => (
                  <div key={p.part_number} className="p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="mono text-xs text-sky-300">{p.part_number}</span>
                      {p.is_mission_critical && <Tag severity="CRITICAL">MC</Tag>}
                      {p.is_single_source && <Tag severity="HIGH">SS</Tag>}
                      <span className="text-xs text-slate-400 truncate">{p.name}</span>
                    </div>
                    <div className="text-xs text-slate-500">
                      {p.quantity_on_hand} on hand · {p.days_of_stock < 0 ? 'no consumption data' : `${p.days_of_stock}d of stock`}
                      {p.gap_days > 0 && <span className="text-orange-400"> · {p.gap_days}d gap</span>}
                      {p.affected_tail_numbers.length > 0 && (
                        <span> · tails: <span className="mono text-slate-400">{p.affected_tail_numbers.slice(0, 3).join(', ')}{p.affected_tail_numbers.length > 3 ? '…' : ''}</span></span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Cascading intel + mitigation */}
            <div className="bg-gray-950/50 border border-gray-800 rounded-lg overflow-hidden flex flex-col">
              <div className="px-4 py-2.5 border-b border-gray-800 flex items-center gap-2">
                <Radio size={13} className="text-sky-400" />
                <h3 className="text-sm font-semibold text-slate-200">Cascading intel & mitigation playbook</h3>
              </div>
              <div className="p-3 space-y-3 max-h-[260px] overflow-y-auto">
                {impact.cascading_signals.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5">Active signals</div>
                    <div className="space-y-1">
                      {impact.cascading_signals.slice(0, 4).map((s, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <Tag severity={s.severity} />
                          <span className="text-slate-500 mono text-[10px]">{s.source}</span>
                          <span className="text-slate-300 truncate flex-1">{s.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5">Recommended actions</div>
                  <ol className="text-xs text-slate-300 space-y-1.5 list-decimal list-inside">
                    {impact.mitigation_actions.map((a, i) => <li key={i}>{a}</li>)}
                  </ol>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Brief modal */}
      {briefOpen && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={() => setBriefOpen(false)}>
          <div onClick={e => e.stopPropagation()} className="bg-gray-950 border border-gray-700 rounded-xl max-w-3xl w-full max-h-[80vh] flex flex-col overflow-hidden">
            <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-800">
              <FileText size={14} className="text-emerald-400" />
              <h3 className="font-semibold text-slate-100">Executive Brief</h3>
              <span className="text-xs text-slate-500">{horizon}-day horizon</span>
              <div className="flex-1" />
              <button onClick={printBrief} className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 rounded border border-emerald-500/30">
                <FileText size={12} />
                Print / Save as PDF
              </button>
              <button onClick={copyBrief} className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-slate-300 rounded border border-gray-700">
                {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                {copied ? 'Copied' : 'Copy markdown'}
              </button>
              <button onClick={() => setBriefOpen(false)} className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-slate-300 rounded border border-gray-700">Close</button>
            </div>
            <pre className="text-xs text-slate-200 whitespace-pre-wrap p-5 overflow-y-auto leading-relaxed font-sans">{brief}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
