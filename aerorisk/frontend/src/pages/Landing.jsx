import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Shield, ArrowRight, Bot, FileCode2, Radio, Target, Plane,
  ShieldCheck, Activity, Zap, Lock, GitBranch, Sparkles, ChevronRight,
  AlertOctagon, DollarSign, Clock, Layers, ExternalLink,
} from 'lucide-react'
import { landingAPI } from '../api/client'

function fmt(n) {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

export default function Landing() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    landingAPI.stats()
      .then(r => setStats(r.data))
      .catch(() => setStats({}))   // page must render even if backend's down
  }, [])

  const sampleHref = stats?.latest_share_token ? `/share/${stats.latest_share_token}` : '/impact'

  return (
    <div className="min-h-screen bg-gray-950 text-slate-100 overflow-x-hidden">
      {/* Animated gradient orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute -top-32 -left-32 w-[480px] h-[480px] rounded-full bg-sky-500/10 blur-3xl" />
        <div className="absolute top-1/3 -right-32 w-[420px] h-[420px] rounded-full bg-indigo-500/10 blur-3xl" />
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] rounded-full bg-red-500/5 blur-3xl" />
      </div>

      <div className="relative">
        <Nav />
        <Hero stats={stats} sampleHref={sampleHref} />
        <LiveNumbers stats={stats} />
        <Wedge />
        <HowItWorks />
        <SampleReport stats={stats} sampleHref={sampleHref} />
        <TrustStrip />
        <CtaFooter sampleHref={sampleHref} />
        <Footer />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Nav
// ---------------------------------------------------------------------------

function Nav() {
  return (
    <header className="border-b border-gray-900/60 bg-gray-950/60 backdrop-blur sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-6">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-sky-500/10 border border-sky-500/30 rounded">
            <Shield size={16} className="text-sky-400" />
          </div>
          <div>
            <div className="font-bold text-sm text-slate-100">AeroRisk AI</div>
            <div className="text-[9px] text-slate-500 -mt-0.5 uppercase tracking-widest">Supply Chain Intelligence</div>
          </div>
        </div>
        <nav className="hidden md:flex items-center gap-5 text-xs text-slate-400 ml-4">
          <a href="#wedge" className="hover:text-slate-200">Why it's different</a>
          <a href="#how" className="hover:text-slate-200">How it works</a>
          <a href="#sample" className="hover:text-slate-200">Sample report</a>
          <a href="#trust" className="hover:text-slate-200">Security</a>
        </nav>
        <div className="flex-1" />
        <Link to="/" className="text-xs text-slate-300 hover:text-slate-100">Sign in</Link>
        <Link
          to="/"
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 text-sky-100 rounded font-semibold transition"
        >
          Launch demo <ArrowRight size={12} />
        </Link>
      </div>
    </header>
  )
}

// ---------------------------------------------------------------------------
// Hero
// ---------------------------------------------------------------------------

function Hero({ stats, sampleHref }) {
  return (
    <section className="max-w-6xl mx-auto px-6 pt-16 md:pt-24 pb-12">
      <div className="grid lg:grid-cols-12 gap-10 items-start">
        <div className="lg:col-span-7 space-y-6">
          <div className="inline-flex items-center gap-2 text-[10px] uppercase tracking-widest px-2.5 py-1 rounded-full border border-sky-500/30 bg-sky-500/10 text-sky-300">
            <Sparkles size={10} />
            For aerospace primes &amp; defense MRO
          </div>
          <h1 className="text-4xl md:text-6xl font-bold leading-[1.05] tracking-tight">
            Find the parts that ground your fleet
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-sky-300 via-sky-400 to-indigo-400">
              before the supplier emails you.
            </span>
          </h1>
          <p className="text-base md:text-lg text-slate-400 leading-relaxed max-w-2xl">
            AeroRisk AI watches OFAC, CISA KEV, NVD, EDGAR and your SBOM feed continuously.
            When a critical signal hits — a sanction, an exploit, a 10-K going dark —
            it simulates the operational ripple all the way down to specific tail numbers,
            writes the executive brief, and pings the responsible engineer.
            <span className="text-slate-200"> No analyst in the loop, no fixed dashboards to refresh.</span>
          </p>
          <div className="flex flex-wrap gap-3 pt-2">
            <Link
              to="/"
              className="group flex items-center gap-2 px-5 py-3 bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 text-sky-100 rounded-lg font-semibold transition"
            >
              <Activity size={15} />
              Open the live demo
              <ArrowRight size={14} className="group-hover:translate-x-0.5 transition" />
            </Link>
            <a
              href={sampleHref}
              target="_blank" rel="noreferrer"
              className="group flex items-center gap-2 px-5 py-3 bg-gray-900/60 hover:bg-gray-900 border border-gray-700 text-slate-200 rounded-lg font-semibold transition"
            >
              <ExternalLink size={14} />
              View a real generated report
            </a>
          </div>
          <div className="flex flex-wrap gap-4 text-[11px] text-slate-500 pt-2">
            <span className="flex items-center gap-1.5"><Lock size={11} /> Self-hosted</span>
            <span className="flex items-center gap-1.5"><ShieldCheck size={11} /> NIST 800-53 audit log</span>
            <span className="flex items-center gap-1.5"><GitBranch size={11} /> Open architecture · no LLM black box</span>
          </div>
        </div>

        {/* Right column: a "live signal" mock that pulses */}
        <div className="lg:col-span-5">
          <HeroMockCard stats={stats} />
        </div>
      </div>
    </section>
  )
}

function HeroMockCard({ stats }) {
  return (
    <div className="relative">
      {/* Glow */}
      <div className="absolute -inset-1 bg-gradient-to-br from-sky-500/20 via-indigo-500/10 to-transparent rounded-2xl blur" />
      <div className="relative bg-gray-900/90 border border-gray-800 rounded-xl overflow-hidden shadow-2xl">
        {/* Window chrome */}
        <div className="flex items-center gap-1.5 px-3 py-2 border-b border-gray-800 bg-gray-950/50">
          <div className="w-2 h-2 rounded-full bg-red-500/60" />
          <div className="w-2 h-2 rounded-full bg-yellow-500/60" />
          <div className="w-2 h-2 rounded-full bg-emerald-500/60" />
          <div className="flex-1" />
          <div className="text-[9px] mono text-slate-500">aerorisk.ai / impact</div>
        </div>
        {/* Body */}
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded border border-red-500/40 bg-red-500/20 text-red-300 animate-pulse">CRITICAL</span>
            <span className="text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded border border-orange-500/40 bg-orange-500/20 text-orange-300">AUTO-TRIGGERED</span>
            <div className="flex-1" />
            <span className="text-[9px] mono text-slate-500">12s ago</span>
          </div>
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Trigger</div>
            <div className="text-xs text-slate-300">
              <span className="mono text-sky-300">CISA_KEV</span> · CVE-2026-31402 added — Honeywell Experion PKS
            </div>
          </div>
          <div className="border-t border-gray-800 pt-3">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Reconstructed impact</div>
            <div className="text-sm text-slate-100 leading-snug italic border-l-2 border-sky-500/60 pl-2.5">
              Honeywell going dark today exposes $14.2M and grounds 8 F-35As within 60 days
              — 3 alternates qualified, swap kicks off in 22 days.
            </div>
          </div>
          <div className="grid grid-cols-4 gap-2 pt-1">
            <Stat icon={DollarSign} value="$14.2M" label="Exposure" color="red" />
            <Stat icon={Plane} value="8" label="Aircraft" color="orange" />
            <Stat icon={Clock} value="22d" label="Swap" color="yellow" />
            <Stat icon={ShieldCheck} value="92%" label="Confidence" color="emerald" />
          </div>
          <div className="text-[10px] text-slate-500 pt-2 border-t border-gray-800 mt-2">
            <Bot size={10} className="inline mr-1 text-sky-400" />
            Brief auto-generated · Sent to <span className="mono text-slate-300">#supply-chain-ops</span> ·
            Shareable link active
          </div>
        </div>
      </div>

      {/* "Live ticker" pill */}
      <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-500">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="mono">
          {stats?.intel_signals_24h != null ? `${fmt(stats.intel_signals_24h)} signals ingested in the last 24h` : 'pulling live signals…'}
        </span>
      </div>
    </div>
  )
}

function Stat({ icon: Icon, value, label, color }) {
  const c = {
    red: 'text-red-300', orange: 'text-orange-300',
    yellow: 'text-yellow-300', emerald: 'text-emerald-300',
  }[color]
  return (
    <div className="bg-gray-950/50 border border-gray-800 rounded-lg p-2">
      <div className="flex items-center gap-1 text-[9px] uppercase tracking-wider text-slate-500">
        <Icon size={9} className={c} />
        {label}
      </div>
      <div className={`text-sm font-bold ${c} mt-0.5`}>{value}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Live numbers strip
// ---------------------------------------------------------------------------

function LiveNumbers({ stats }) {
  const items = [
    { label: 'Aircraft monitored', value: stats?.aircraft_monitored },
    { label: 'Suppliers tracked', value: stats?.suppliers_tracked },
    { label: 'Signals ingested', value: stats?.intel_signals_total },
    { label: 'Scenarios generated', value: stats?.scenarios_generated },
    { label: 'CVEs cross-referenced', value: stats?.cves_cross_referenced },
  ]
  return (
    <section className="border-y border-gray-900/80 bg-gray-950/60">
      <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-5 gap-6">
        {items.map((it) => (
          <div key={it.label}>
            <div className="text-2xl md:text-3xl font-bold mono text-slate-100">{fmt(it.value)}</div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500 mt-0.5">{it.label}</div>
          </div>
        ))}
      </div>
      <div className="max-w-6xl mx-auto px-6 pb-3 text-[10px] text-slate-600">
        Live counts pulled from the running instance. Every number is reconstructible from the underlying data model — no synthetic embeddings, no LLM hallucination.
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// The wedge — 3 columns
// ---------------------------------------------------------------------------

function Wedge() {
  const cards = [
    {
      icon: Bot,
      tint: 'sky',
      title: 'Autonomous, not analyst-on-call',
      body: 'A new CRITICAL signal becomes a persisted scenario, an executive brief, and a Slack ping in under 60 seconds — without anyone refreshing a dashboard.',
      proof: '60-second loop · OFAC, KEV, NVD, EDGAR · webhook / Slack out',
    },
    {
      icon: FileCode2,
      tint: 'indigo',
      title: 'Cyber-physical, all the way down',
      body: 'Upload a CycloneDX SBOM. Components match the part catalog, CVEs from NVD + KEV + CISA ICS attach to every line, then it rolls up to "these 8 F-35As are exposed" — not "vendor X has a CVE."',
      proof: 'SBOM → CVE → tail number · what other tools stop at "vendor"',
    },
    {
      icon: Target,
      tint: 'rose',
      title: 'Reconstructible, not vibes',
      body: 'Every number on every page traces back to the data model. No embeddings, no hallucinated summaries, no "the AI says trust us." Ship the report to a buyer without lawyering it first.',
      proof: 'Audit log · share-token public reports · self-hosted option',
    },
  ]
  return (
    <section id="wedge" className="max-w-6xl mx-auto px-6 py-20">
      <div className="max-w-3xl mb-12">
        <div className="text-[10px] uppercase tracking-widest text-sky-400 mb-3">Why it's different</div>
        <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
          Three things every other supply-chain tool gets wrong.
        </h2>
      </div>
      <div className="grid md:grid-cols-3 gap-5">
        {cards.map((c) => (
          <WedgeCard key={c.title} {...c} />
        ))}
      </div>
    </section>
  )
}

function WedgeCard({ icon: Icon, tint, title, body, proof }) {
  const tints = {
    sky: { border: 'border-sky-500/30', bg: 'bg-sky-500/10', text: 'text-sky-300' },
    indigo: { border: 'border-indigo-500/30', bg: 'bg-indigo-500/10', text: 'text-indigo-300' },
    rose: { border: 'border-rose-500/30', bg: 'bg-rose-500/10', text: 'text-rose-300' },
  }[tint]
  return (
    <div className="bg-gray-900/40 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition">
      <div className={`inline-flex p-2 rounded-lg ${tints.bg} border ${tints.border} mb-4`}>
        <Icon size={18} className={tints.text} />
      </div>
      <h3 className="text-lg font-semibold text-slate-100 mb-2">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed mb-4">{body}</p>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 border-t border-gray-800 pt-3">{proof}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// How it works — visual pipeline
// ---------------------------------------------------------------------------

function HowItWorks() {
  const steps = [
    { icon: Radio, label: 'Signal', sub: 'OFAC · KEV · NVD · EDGAR · SBOM' },
    { icon: Layers, label: 'Match', sub: 'Fuzzy supplier + part catalog' },
    { icon: AlertOctagon, label: 'Impact', sub: 'Aircraft × parts × cost × time' },
    { icon: FileCode2, label: 'Brief', sub: 'Executive markdown + PDF' },
    { icon: Zap, label: 'Notify', sub: 'Slack · webhook · audit log' },
  ]
  return (
    <section id="how" className="border-y border-gray-900/80 bg-gradient-to-b from-gray-950 to-gray-950/40">
      <div className="max-w-6xl mx-auto px-6 py-20">
        <div className="max-w-3xl mb-10">
          <div className="text-[10px] uppercase tracking-widest text-sky-400 mb-3">How it works</div>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
            One loop, end to end. No glue code on your side.
          </h2>
          <p className="text-slate-400 mt-3 max-w-2xl">
            The autonomous cycle runs every 60 seconds. Drop in a CycloneDX feed, point it at a Slack webhook, and the system runs itself.
          </p>
        </div>
        <div className="flex items-stretch gap-3 overflow-x-auto pb-2">
          {steps.map((s, i) => (
            <div key={s.label} className="flex items-stretch gap-3 shrink-0">
              <div className="flex flex-col items-center bg-gray-900/60 border border-gray-800 rounded-xl px-5 py-4 min-w-[150px]">
                <div className="p-2 bg-sky-500/10 border border-sky-500/30 rounded-lg mb-2">
                  <s.icon size={16} className="text-sky-300" />
                </div>
                <div className="text-sm font-semibold text-slate-100">{s.label}</div>
                <div className="text-[10px] text-slate-500 text-center mt-1 leading-tight">{s.sub}</div>
              </div>
              {i < steps.length - 1 && (
                <div className="flex items-center text-slate-700">
                  <ChevronRight size={20} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Sample report CTA
// ---------------------------------------------------------------------------

function SampleReport({ stats, sampleHref }) {
  const hasReal = !!stats?.latest_share_token
  return (
    <section id="sample" className="max-w-6xl mx-auto px-6 py-20">
      <div className="grid md:grid-cols-2 gap-10 items-center">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-sky-400 mb-3">Sample report</div>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight mb-4">
            See a real one before you talk to us.
          </h2>
          <p className="text-slate-400 leading-relaxed mb-6">
            Every scenario the system generates is shareable as a public, read-only URL.
            No login, no sales call, no "request a demo." Click below to see the most
            recent CRITICAL scenario this instance produced.
          </p>
          <a
            href={sampleHref}
            target="_blank" rel="noreferrer"
            className="group inline-flex items-center gap-2 px-5 py-3 bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/40 text-sky-100 rounded-lg font-semibold transition"
          >
            <ExternalLink size={14} />
            {hasReal ? 'View the latest live report' : 'Generate one in the demo first'}
            <ArrowRight size={14} className="group-hover:translate-x-0.5 transition" />
          </a>
          {!hasReal && (
            <div className="text-[11px] text-slate-500 mt-3">
              No scenarios in the running instance yet — the agent generates them automatically on startup, but you can also kick one off from the dashboard's Operational Impact page.
            </div>
          )}
        </div>
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 space-y-4">
          <div className="text-[10px] uppercase tracking-widest text-slate-500">A typical report contains</div>
          <ul className="space-y-2.5 text-sm text-slate-300">
            {[
              'A one-line executive summary that fits in a Slack message',
              'Dollar exposure over the chosen horizon, with the math shown',
              'Specific tail numbers + squadrons + days-to-impact',
              'Ranked alternates with overlapping-part counts and OTD',
              'Cascading intel signals (KEV chains, sanction overlaps)',
              'A 5-step mitigation playbook ready to assign',
            ].map((line) => (
              <li key={line} className="flex gap-2">
                <ChevronRight size={14} className="text-sky-400 shrink-0 mt-0.5" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Trust strip
// ---------------------------------------------------------------------------

function TrustStrip() {
  const items = [
    { icon: Lock, label: 'JWT auth + RBAC', sub: 'bcrypt at rest · 3-role model' },
    { icon: Shield, label: 'Multi-tenant isolation', sub: 'Per-tenant scoping at the query layer' },
    { icon: Activity, label: 'Append-only audit log', sub: 'AU-2 baseline · denormalized for forensics' },
    { icon: GitBranch, label: 'Self-hosted ready', sub: 'Single Dockerfile · SQLite or Postgres' },
  ]
  return (
    <section id="trust" className="border-y border-gray-900/80 bg-gray-950/60">
      <div className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <div className="text-[10px] uppercase tracking-widest text-sky-400 mb-3">Built for the deployment realities</div>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-100">
            Procurement won't reject it on the security checklist.
          </h2>
        </div>
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
          {items.map((it) => (
            <div key={it.label} className="bg-gray-900/40 border border-gray-800 rounded-lg p-4">
              <it.icon size={16} className="text-sky-300 mb-2" />
              <div className="text-sm font-semibold text-slate-100">{it.label}</div>
              <div className="text-[11px] text-slate-500 mt-0.5">{it.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// CTA footer
// ---------------------------------------------------------------------------

function CtaFooter({ sampleHref }) {
  return (
    <section className="max-w-6xl mx-auto px-6 py-24">
      <div className="relative bg-gradient-to-br from-sky-500/15 via-indigo-500/10 to-gray-900/60 border border-sky-500/30 rounded-2xl p-10 md:p-14 text-center overflow-hidden">
        <div className="absolute -top-20 left-1/2 -translate-x-1/2 w-[400px] h-[400px] rounded-full bg-sky-500/10 blur-3xl" />
        <div className="relative">
          <h2 className="text-3xl md:text-5xl font-bold text-slate-100 leading-tight">
            The next CRITICAL signal will hit
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-sky-300 to-indigo-400">
              with or without you watching.
            </span>
          </h2>
          <p className="text-slate-400 mt-5 max-w-2xl mx-auto">
            The demo is the real product running on real public feeds. Click through, upload your own SBOM, and break it.
          </p>
          <div className="flex flex-wrap gap-3 justify-center mt-8">
            <Link
              to="/"
              className="group flex items-center gap-2 px-6 py-3 bg-sky-500/30 hover:bg-sky-500/40 border border-sky-500/50 text-white rounded-lg font-semibold transition"
            >
              <Activity size={15} />
              Launch the demo
              <ArrowRight size={14} className="group-hover:translate-x-0.5 transition" />
            </Link>
            <a
              href={sampleHref}
              target="_blank" rel="noreferrer"
              className="flex items-center gap-2 px-6 py-3 bg-gray-900/60 hover:bg-gray-900 border border-gray-700 text-slate-200 rounded-lg font-semibold transition"
            >
              <ExternalLink size={14} />
              See a real report
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-gray-900/80">
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-wrap items-center gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <Shield size={12} className="text-sky-400" />
          <span className="text-slate-400">AeroRisk AI</span>
        </div>
        <span>·</span>
        <span>Autonomous aerospace supply chain intelligence</span>
        <div className="flex-1" />
        <span className="mono">v1.0.0</span>
      </div>
    </footer>
  )
}
